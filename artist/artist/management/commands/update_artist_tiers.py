from django.core.management.base import BaseCommand
from django.utils import timezone
from artist.models import Artist, CommissionSettings
from artist.services import TierManager

class Command(BaseCommand):
    help = 'Update artist tiers based on the configured frequency'

    def handle(self, *args, **options):
        settings = CommissionSettings.objects.first()
        last_update = settings.last_tier_update
        if not last_update or (timezone.now() - last_update).days >= settings.tier_update_frequency:
            tier_manager = TierManager()
            for artist in Artist.objects.all():
                tier_manager.update_tier(artist)
            settings.last_tier_update = timezone.now()
            settings.save()
            self.stdout.write(self.style.SUCCESS('Successfully updated artist tiers'))
        else:
            self.stdout.write(self.style.WARNING('Tier update not due yet'))