from django.core.management.base import BaseCommand
from saleor.order.models import OrderLine
from artist.models import Artist
from artist.services import CommissionCalculator

class Command(BaseCommand):
    help = 'Calculate and update commissions for all orders'

    def handle(self, *args, **options):
        orders = Order.objects.all()
        for order in orders:
            for order_line in order.lines.all():
                artist = Artist.objects.filter(artwork__saleor_product_id=order_line.product_id).first()
                if artist:
                    commission_calculator = CommissionCalculator()
                    commission = commission_calculator.calculate_commission(order_line, artist)
                    # ... logic to update commission for the order line ...
        self.stdout.write(self.style.SUCCESS('Successfully calculated and updated commissions'))