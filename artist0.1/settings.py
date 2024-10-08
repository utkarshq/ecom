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

# Add these settings if they're not already present
from django.utils.translation import gettext_lazy as _

LANGUAGE_CODE = 'en-us'

LANGUAGES = [
    ('en', _('English')),
    ('hi', _('Hindi')),
    ('ms', _('Malay')),
    ('th', _('Thai')),
    ('ur', _('Urdu')),
    ('bn', _('Bengali')),
    ('ta', _('Tamil')),
    ('te', _('Telugu')),
    ('ur', _('Urdu')),
    ('bn', _('Bengali')),
    ('ta', _('Tamil')),
    # Add more languages as needed
]

USE_I18N = True
USE_L10N = True

LOCALE_PATHS = [
    os.path.join(BASE_DIR, 'locale'),
]

MIDDLEWARE = [
    # ... other middleware ...
    'django.middleware.locale.LocaleMiddleware',
    # ... other middleware ...
]