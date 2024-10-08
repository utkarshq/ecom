from django.core.management.base import BaseCommand
from .tasks import update_artist_tiers

class Command(BaseCommand):
    help = 'Update artist tiers'

    def handle(self, *args, **options):
        update_artist_tiers.delay()