import logging

from celery.utils.log import get_task_logger
from django.conf import settings
from django.core.files.storage import default_storage
from django.db.models import Exists, OuterRef
from django.utils import timezone

from ..celeryconf import app
from . import private_storage
from .models import EventDelivery, EventPayload

task_logger: logging.Logger = get_task_logger(__name__)

# Batch size was tested on db with 1mln payloads and deliveries, each delivery
# had multiple attempts. One task took less than 0,5 second, memory usage didn't raise
# more than 100 MB.
BATCH_SIZE = 1000


@app.task
def delete_from_storage_task(path):
    default_storage.delete(path)


@app.task
def delete_event_payloads_task(expiration_date=None):
    expiration_date = (
        expiration_date
        or timezone.now() + settings.EVENT_PAYLOAD_DELETE_TASK_TIME_LIMIT
    )
    delete_period = timezone.now() - settings.EVENT_PAYLOAD_DELETE_PERIOD
    valid_deliveries = EventDelivery.objects.filter(created_at__gt=delete_period)
    payloads_to_delete = EventPayload.objects.filter(
        ~Exists(valid_deliveries.filter(payload_id=OuterRef("id")))
    ).order_by("-pk")
    ids = list(payloads_to_delete.values_list("pk", flat=True)[:BATCH_SIZE])
    qs = EventPayload.objects.filter(pk__in=ids)
    if ids:
        if expiration_date > timezone.now():
            files_to_delete = [
                event_payload.payload_file.name
                for event_payload in qs.using(settings.DATABASE_CONNECTION_REPLICA_NAME)
                if event_payload.payload_file
            ]
            qs.delete()
            delete_files_from_private_storage_task.delay(files_to_delete)
            delete_event_payloads_task.delay(expiration_date)
        else:
            task_logger.error("Task invocation time limit reached, aborting task")


@app.task
def delete_files_from_storage_task(paths):
    for path in paths:
        default_storage.delete(path)


@app.task
def delete_files_from_private_storage_task(paths):
    for path in paths:
        private_storage.delete(path)
