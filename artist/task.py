from celery import shared_task
from django.core.management import call_command
from django.db import transaction

@shared_task
def recalculate_artist_tiers():
    with transaction.atomic():
        call_command('recalculate_artist_tiers')