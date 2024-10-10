from decimal import Decimal
from artist.models import Artist, TierConfiguration, ReferralLink, Commission, CommissionSettings
from saleor.order.models import OrderLine
from saleor.product.models import ProductType
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.admin.models import LogEntry, CHANGE
from django.contrib.contenttypes.models import ContentType
from django.db import transaction

class CommissionService:
    @staticmethod
    def calculate_commission(order_line: OrderLine, artist: Artist) -> Decimal:
        """
        Calculates the commission amount for a given order line and artist.

        Args:
            order_line: The order line for which the commission is being calculated.
            artist: The artist associated with the order line.

        Returns:
            Decimal: The commission amount.
        """
        commission_settings = CommissionSettings.objects.first()
        product_type_commission = CommissionService.get_product_type_commission(order_line.product.product_type, commission_settings)
        sales_type_commission = CommissionService.get_sales_type_commission(order_line, commission_settings)
        tier_commission = CommissionService.get_tier_commission(artist, commission_settings)

        commission_rates = [product_type_commission, sales_type_commission, tier_commission]
        highest_commission_rate = max(filter(None, commission_rates), default=0)

        return order_line.unit_price_gross * highest_commission_rate / 100

    @staticmethod
    def get_product_type_commission(product_type: ProductType, commission_settings: CommissionSettings) -> Decimal:
        """
        Retrieves the commission rate for a specific product type.

        Args:
            product_type: The product type for which the commission rate is being retrieved.
            commission_settings: The commission settings object.

        Returns:
            Decimal: The commission rate for the product type.
        """
        return commission_settings.product_type_commissions.get(str(product_type.pk), Decimal(0))

    @staticmethod
    def get_sales_type_commission(order_line: OrderLine, commission_settings: CommissionSettings) -> Decimal:
        """
        Retrieves the commission rate for a specific sales type (referral link or voucher).

        Args:
            order_line: The order line for which the commission rate is being retrieved.
            commission_settings: The commission settings object.

        Returns:
            Decimal: The commission rate for the sales type.
        """
        referral_link = ReferralLink.objects.filter(
            product=order_line.product,
            code__in=order_line.variant.metadata.get('referral_code', [])
        ).first()
        if referral_link:
            return commission_settings.referral_link_commission_rate
        return Decimal(0)

    @staticmethod
    def get_tier_commission(artist: Artist, commission_settings: CommissionSettings) -> Decimal:
        """
        Retrieves the commission rate for the artist's tier.

        Args:
            artist: The artist for which the commission rate is being retrieved.
            commission_settings: The commission settings object.

        Returns:
            Decimal: The commission rate for the artist's tier.
        """
        if artist.tier:
            return commission_settings.tier_commissions.get(artist.tier.tier, Decimal(0))
        return Decimal(0)

    @staticmethod
    def create_commission(order_line: OrderLine, artist: Artist):
        """
        Creates a new commission record for a given order line and artist.

        Args:
            order_line: The order line for which the commission is being created.
            artist: The artist associated with the order line.
        """
        commission_amount = CommissionService.calculate_commission(order_line, artist)
        if commission_amount > 0:
            Commission.objects.create(
                artist=artist,
                order_line=order_line,
                amount=commission_amount
            )

    @staticmethod
    def update_commission_status(order_line: OrderLine):
        """
        Updates the commission status for an order line if it's cancelled or returned.
        """
        if order_line.status in ['cancelled', 'returned']:
            commissions = Commission.objects.filter(order_line=order_line, status='PENDING')
            for commission in commissions:
                commission.status = 'CANCELLED'
                commission.save()

    @staticmethod
    def pay_commissions():
        """
        Pays out commissions that are due based on the commission period.
        """
        commission_settings = CommissionSettings.objects.first()
        commissions = Commission.objects.filter(status='PENDING')
        for commission in commissions:
            if (timezone.now() - commission.created_at).days >= commission_settings.commission_period:
                commission.status = 'PAID'
                commission.paid_at = timezone.now()
                commission.save()

# Signal handlers will call the CommissionService methods
@receiver(post_save, sender=OrderLine)
def handle_order_line_save(sender, instance, created, **kwargs):
    """
    Handles the post-save signal for OrderLine.
    Creates a commission record if the order line is created.
    Updates commission status if the order line is updated.
    """
    if created:
        artist = Artist.objects.filter(artwork__saleor_product_id=instance.product_id).first()
        if artist:
            CommissionService.create_commission(instance, artist)
    else:
        # Handle updates to the order line, such as cancellations or returns
        CommissionService.update_commission_status(instance)

    # Run auto-pay after any OrderLine save
    CommissionManager.auto_pay_commissions()

class CommissionManager:
    @staticmethod
    def auto_pay_commissions():
        """
        Automatically credits commissions to artists' accounts that are due based on the commission period.
        """
        commission_settings = CommissionSettings.objects.first()
        pending_commissions = Commission.objects.filter(status='PENDING')
        
        for commission in pending_commissions:
            if (timezone.now() - commission.created_at).days >= commission_settings.commission_period:
                CommissionManager.credit_commission(commission)

    @staticmethod
    def credit_commission(commission):
        """
        Credits a single commission to the artist's account and logs the transaction.
        """
        if commission.status == 'PENDING':
            with transaction.atomic():
                commission.status = 'CREDITED'
                commission.paid_at = timezone.now()
                commission.save()

                # Update artist's commission account
                artist = commission.artist
                artist.commission_wallet += commission.amount
                artist.save()

                # Log the credit transaction
                CommissionManager.log_commission_credit(commission)

            return True
        return False

    @staticmethod
    def log_commission_credit(commission):
        """
        Logs the commission credit transaction.
        """
        from django.contrib.admin.models import LogEntry, CHANGE
        from django.contrib.contenttypes.models import ContentType

        LogEntry.objects.log_action(
            user_id=1,  # System user ID (you may want to create a specific user for this)
            content_type_id=ContentType.objects.get_for_model(Commission).pk,
            object_id=commission.pk,
            object_repr=str(commission),
            action_flag=CHANGE,
            change_message=f"Commission credited: ${commission.amount} to artist {commission.artist.username}"
        )

    @staticmethod
    def pay_artist_balance(artist):
        """
        Pays out the entire balance in the artist's commission account.
        """
        credited_commissions = Commission.objects.filter(artist=artist, status='CREDITED')
        total_paid = Decimal('0.00')

        for commission in credited_commissions:
            commission.status = 'PAID'
            commission.save()
            total_paid += commission.amount
            CommissionManager.log_commission_payment(commission)

        artist.total_commission -= total_paid
        artist.save()

        return total_paid

    @staticmethod
    def log_commission_payment(commission):
        """
        Logs the commission payment.
        """
        from django.contrib.admin.models import LogEntry, CHANGE
        from django.contrib.contenttypes.models import ContentType

        LogEntry.objects.log_action(
            user_id=1,  # System user ID (you may want to create a specific user for this)
            content_type_id=ContentType.objects.get_for_model(Commission).pk,
            object_id=commission.pk,
            object_repr=str(commission),
            action_flag=CHANGE,
            change_message=f"Commission paid: ${commission.amount} to artist {commission.artist.username}"
        )

class CommissionSettings(models.Model):
    """
    Model for managing commission settings.
    """
    commission_period = models.PositiveIntegerField(default=14)
    referral_link_commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    product_type_commissions = models.JSONField(default=dict)  # Store as {product_type_id: rate}
    tier_commissions = models.JSONField(default=dict)  # Store as {tier_name: rate}

    def __str__(self):
        return f"Commission Period: {self.commission_period} days"