import random
import string
from decimal import Decimal
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from saleor.order.models import OrderLine
from saleor.discount.models import Voucher, VoucherType
from saleor.discount.utils import generate_voucher_code
import hashlib
from django.conf import settings
from .commission import CommissionService
from artist.models import ReferralLink

class ReferralLinkService:
    @staticmethod
    def _generate_unique_code(length=12):
        """Generates a unique alphanumeric code for referral links."""
        while True:
            code = ''.join(random.choices(string.ascii_letters + string.digits, k=length))
            if not ReferralLink.objects.filter(code=code).exists():
                return code

    @staticmethod
    def generate_referral_link(artist: Artist, product: Product = None, referrer: Artist = None, link_type: str = ReferralLink.ReferralLinkType.ARTIST_SELF) -> ReferralLink:
        """Generates a unique referral link for various referral scenarios."""

        code = ReferralLinkService._generate_unique_code()
        expiry_date = None
        commission_settings = CommissionSettings.objects.first()

        if link_type == ReferralLink.ReferralLinkType.PRODUCT_SELF:
            expiry_date = timezone.now() + timezone.timedelta(days=commission_settings.product_referral_link_expiry_days)
        
        referral_link = ReferralLink.objects.create(
            artist=artist,
            product=product,  # None for artist profile referrals
            referrer=referrer,  # None for self-referrals
            code=code,
            link_type=link_type,
            expires_at=expiry_date
        )
        return referral_link

    @staticmethod
    def apply_referral(order_line: OrderLine, referral_code: str):
        """Applies a referral (link or voucher) to an order line and calculates commissions."""
        try:
            referral_link = ReferralLink.objects.get(code=referral_code)
        except ReferralLink.DoesNotExist:
            raise ValidationError("Invalid referral code.")

        commission_settings = CommissionSettings.objects.first()

        if referral_link.is_voucher_referral:
            # Apply voucher logic (similar to previous implementation)
            pass  

        else:
            # Referral Link Logic
            if referral_link.link_type == ReferralLink.ReferralLinkType.ARTIST_SELF:
                discount_percentage = commission_settings.artist_self_referral_discount
            elif referral_link.link_type == ReferralLink.ReferralLinkType.PRODUCT_SELF:
                discount_percentage = commission_settings.artist_self_product_referral_discount
            elif referral_link.link_type == ReferralLink.ReferralLinkType.ARTIST_CROSS:
                discount_percentage = commission_settings.artist_cross_referral_discount
            elif referral_link.link_type == ReferralLink.ReferralLinkType.PRODUCT_CROSS:
                discount_percentage = commission_settings.artist_cross_product_referral_discount
            else:
                raise ValidationError("Invalid referral link type.")

            discount_amount = (order_line.unit_price * discount_percentage) / Decimal(100)

            # Create and apply a voucher
            voucher = Voucher.objects.create(
                code=generate_voucher_code(),
                type=VoucherType.ENTIRE_ORDER,
                discount_value_type='fixed',
                discount_value=discount_amount,
                usage_limit=1,
            )
            order_line.voucher = voucher
            order_line.save()

            # Commission Calculation
            commission_service = CommissionService()
            if referral_link.link_type in [ReferralLink.ReferralLinkType.ARTIST_CROSS, ReferralLink.ReferralLinkType.PRODUCT_CROSS]:
                # Cross-referral commission
                commission_service.calculate_cross_referral_commission(order_line, referral_link)
            else:
                # Self-referral commission (existing logic)
                commission_service.calculate_commission(order_line, referral_link.artist)

        # Update referral link usage
        referral_link.times_used += 1
        referral_link.save()

    @staticmethod
    def get_referral_link_by_code(code: str) -> ReferralLink:
        """Retrieves a referral link by its code."""
        try:
            return ReferralLink.objects.get(code=code)
        except ReferralLink.DoesNotExist:
            return None

class ReferralService:
    @staticmethod
    def generate_referral_token(referral_link: ReferralLink) -> str:
        salt = settings.SECRET_KEY  # Use a secure setting
        data = f"{referral_link.code}-{referral_link.product.id}-{salt}"
        token = hashlib.sha256(data.encode()).hexdigest()
        return token

    @staticmethod
    def validate_referral_token(token: str, product_id: int) -> ReferralLink:
        """
        Validates the referral token and returns the ReferralLink if valid.
        """
        referral_links = ReferralLink.objects.filter(product_id=product_id)
        for referral_link in referral_links:
            expected_token = ReferralService.generate_referral_token(referral_link)
            if expected_token == token:
                return referral_link
        return None

    @staticmethod
    def apply_referral(order_data: dict, referral_token: str):
        """
        Applies the referral to the order data if the token is valid.
        """
        try:
            product_id = order_data.get('lines', [{}])[0].get('variant', {}).get('product', {}).get('id')
            if not product_id:
                return

            referral_link = ReferralService.validate_referral_token(referral_token, product_id)
            if referral_link and referral_link.is_valid():
                # Assuming you're storing the referral code in order metadata
                if 'metadata' not in order_data:
                    order_data['metadata'] = {}
                order_data['metadata']['referral_code'] = str(referral_link.code)

                # (Optional) Apply a discount or other benefits here
        except Exception as e:
            # Handle exceptions (e.g., log the error)
            print(f"Error applying referral: {e}")

@receiver(post_save, sender=OrderLine)
def update_referral_link_status(sender, instance: OrderLine, created, **kwargs):
    """Updates the referral link status when an order line is created."""
    if created and instance.variant.metadata.get('referral_code'):
        referral_code = instance.variant.metadata.get('referral_code')
        referral_link = ReferralLinkService.get_referral_link_by_code(referral_code)
        if referral_link:
            referral_link.used = True
            referral_link.save()
