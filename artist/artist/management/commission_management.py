from django.core.management.base import BaseCommand
from saleor.order.models import OrderLine
from artist.models import Artist
from artist.services.commission import CommissionManager

class Command(BaseCommand):
    help = 'Calculate and update commissions for all orders'

    def handle(self, *args, **options):
        orders = Order.objects.all()
        for order in orders:
            for order_line in order.lines.all():
                artist = Artist.objects.filter(artwork__saleor_product_id=order_line.product_id).first()
                if artist:
                    CommissionManager.create_commissions(order_line, artist)
        self.stdout.write(self.style.SUCCESS('Successfully calculated and updated commissions')) 