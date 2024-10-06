import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')

app = Celery('project')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'recalculate-artist-tiers': {
        'task': 'artist.tasks.recalculate_artist_tiers',
        'schedule': crontab(hour=0, minute=0),  # Run daily at midnight
    },
}