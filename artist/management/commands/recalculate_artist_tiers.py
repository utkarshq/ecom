from django.core.management.base import BaseCommand
from django.db.models import Sum
from artist.models import Artist, TierConfiguration 
from saleor.order.models import Order
from artist.artist.services import TierService

class Command(BaseCommand):
    help = 'Recalculate artist tiers based on sales or percentiles'

    def handle(self, *args, **options):
        use_percentile = TierConfiguration.objects.first().use_percentile if TierConfiguration.objects.first() else False

        artists = Artist.objects.annotate(
            total_sales=Sum('user__orders__total_gross_amount')
        ).order_by('-total_sales')

        total_artists = artists.count()

        for index, artist in enumerate(artists):
            if use_percentile:
                percentile = (index + 1) / total_artists * 100
                tier = TierConfiguration.objects.filter(percentile__gte=percentile).order_by('percentile').first()
            else:
                tier = TierConfiguration.objects.filter(sales_threshold__lte=artist.total_sales).order_by('-sales_threshold').first()

            if tier:
                artist.tier = tier
                artist.save()

        self.stdout.write(self.style.SUCCESS('Successfully recalculated artist tiers'))