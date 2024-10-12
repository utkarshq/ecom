from decimal import Decimal
from artist.models import Artist, TierConfiguration, ReferralLink, Commission, CommissionSettings
from saleor.order.models import OrderLine
from saleor.product.models import Product
from django.utils import timezone
from django.db.models import Sum
from django.conf import settings
from django.db import models
from saleor.product.models import ProductType
from saleor.discount.models import Voucher
from saleor.order.models import Order
from django.db.models.signals import post_save
from django.dispatch import receiver
from artist.services.commission import CommissionService
class TierService:
    def get_tier(self, artist: Artist) -> TierConfiguration:
        use_percentile = TierConfiguration.objects.first().use_percentile
        if use_percentile:
            return self.get_tier_by_percentile(artist)
        else:
            return self.get_tier_by_sales_threshold(artist)

    def get_tier_by_percentile(self, artist: Artist) -> TierConfiguration:
        total_artists = Artist.objects.count()
        artists = list(Artist.objects.order_by('-total_sales'))
        index = artists.index(artist)
        percentile = (index + 1) / total_artists * 100
        return TierConfiguration.objects.filter(percentile__gte=percentile).order_by('percentile').first()

    def get_tier_by_sales_threshold(self, artist: Artist) -> TierConfiguration:
        return TierConfiguration.objects.filter(sales_threshold__lte=artist.total_sales).order_by('-sales_threshold').first()

    def update_tier(self, artist: Artist):
        new_tier = self.get_tier(artist)
        if new_tier and new_tier != artist.tier:
            old_tier = artist.tier
            artist.tier = new_tier
            artist.save()
            if new_tier.tier_level > old_tier.tier_level:
                self.notify_tier_upgrade(artist, new_tier)

    def notify_tier_upgrade(self, artist: Artist, new_tier: TierConfiguration):
        # Implement notification logic here
        pass

    def get_monthly_sales(self, artist: Artist) -> Decimal:
        one_month_ago = timezone.now() - relativedelta(months=1)
        monthly_sales = Order.objects.filter(
            user=artist.user,
            created_at__gte=one_month_ago
        ).aggregate(total_sales=Sum('total_gross_amount'))['total_sales'] or 0
        return monthly_sales


@receiver(post_save, sender=OrderLine)
def create_commission(sender, instance, created, **kwargs):
    if created:
        artist = Artist.objects.filter(artwork__saleor_product_id=instance.product_id).first()
        if artist:
            commission_service = CommissionService()
            commission_amount = commission_service.calculate_commission(instance, artist)
            if commission_amount > 0:
                Commission.objects.create(
                    artist=artist,
                    order_line=instance,
                    amount=commission_amount
                )

@receiver(post_save, sender=OrderLine)
def update_commission_status(sender, instance, created, **kwargs):
    if not created:  # Only handle updates, not creation
        # Check if the order line has been cancelled or returned
        if instance.status in ['cancelled', 'returned']:
            # Find any associated commissions
            commissions = Commission.objects.filter(order_line=instance)
            for commission in commissions:
                if commission.status == 'PENDING':
                    commission.status = 'CANCELLED'
                    commission.save()


class CommissionSettings(models.Model):
    commission_period = models.PositiveIntegerField(default=14)

    def __str__(self):
        return f"Commission Period: {self.commission_period} days"