from django.core.management.base import BaseCommand
from artist.models import Artist, TierConfiguration
from django.db.models import Sum
from django.utils import timezone

class Command(BaseCommand):
    help = 'Updates artist tiers based on the current TierConfiguration'

    def handle(self, *args, **options):
        config = TierConfiguration.objects.first()
        if not config:
            self.stdout.write(self.style.ERROR('No TierConfiguration found. Please create one in the admin panel.'))
            return

        artists = Artist.objects.all()

        if config.use_percentile:
            # Percentile-based tier update
            total_artists = artists.count()
            sorted_artists = artists.order_by('-total_sales')
            
            for index, artist in enumerate(sorted_artists):
                percentile = (index + 1) / total_artists * 100
                if percentile <= config.platinum_threshold:
                    artist.tier = TierSettings.objects.get(name='Platinum')
                elif percentile <= config.gold_threshold:
                    artist.tier = TierSettings.objects.get(name='Gold')
                elif percentile <= config.silver_threshold:
                    artist.tier = TierSettings.objects.get(name='Silver')
                elif percentile <= config.new_threshold:
                    artist.tier = TierSettings.objects.get(name='New')
                artist.save()
        else:
            # Sales-based tier update
            for artist in artists:
                if artist.total_sales >= config.platinum_threshold:
                    artist.tier = TierSettings.objects.get(name='Platinum')
                elif artist.total_sales >= config.gold_threshold:
                    artist.tier = TierSettings.objects.get(name='Gold')
                elif artist.total_sales >= config.silver_threshold:
                    artist.tier = TierSettings.objects.get(name='Silver')
                elif artist.total_sales >= config.new_threshold:
                    artist.tier = TierSettings.objects.get(name='New')
                artist.save()

        self.stdout.write(self.style.SUCCESS('Successfully updated artist tiers'))