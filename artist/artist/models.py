from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from saleor.product.models import ProductType
from saleor.order.models import OrderLine
from django.db.models.signals import post_save
from django.dispatch import receiver
from saleor.product.models import Product
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import Permission
import uuid
from saleor.discount.models import Voucher
from saleor.product.models import Product
from django.utils import timezone
import random
from saleor.product.models import ProductType
import string
from django.db.models import Sum


User = get_user_model()

class TierConfiguration(models.Model):
    TIER_CHOICES = (
        ('NEW', 'New'),
        ('EMERGING', 'Emerging'),
        ('POPULAR', 'Popular'),
        ('FAMOUS', 'Famous'),
    )
    tier = models.CharField(max_length=10, choices=TIER_CHOICES, unique=True)
    tier_level = models.PositiveSmallIntegerField(default=0)
    use_percentile = models.BooleanField(default=False)
    threshold = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2)
    tier_info = models.TextField(blank=True)
    tier_perks = models.JSONField(default=list, blank=True)

    def __str__(self):
        threshold_type = "Percentile" if self.use_percentile else "Sales"
        return f"{self.tier} - {threshold_type}: {self.threshold} - Commission: {self.commission_rate}%"

    class Meta:
        ordering = ['tier_level']
        permissions = [('can_view_commission_wallet', 'Can view commission wallet'),
                       ("can_approve_artists", "Can approve artist applications"),
                       ("can_reject_artists", "Can reject artist applications"),
                       ("is_artist", "Is an artist"),]

class Artist(models.Model):
    """
    Represents an artist in the system.

    This model stores information about artists, including their application status,
    personal details, and sales performance. It is linked to the User model and tracks
    the artist's progression through the application process and their tier status.

    Attributes:
        user (User): One-to-one relationship with the User model.
        legal_name (str): The artist's legal name, used for official purposes.
        portfolio_url (str): URL to the artist's portfolio, showcasing their work.
        bio (str): Artist's biography, providing background information.
        social_links (dict): JSON field storing the artist's social media links.
        tier (TierSettings): The artist's current tier based on sales performance.
        application_status (str): Current status of the artist's application process.
        application_date (datetime): Date when the artist initially applied.
        approval_date (datetime): Date when the artist was approved (if applicable).
        total_sales (Decimal): Total sales amount for the artist, used for tier calculation.
        legal_documents (File): Uploaded legal documents for verification purposes.

    Methods:
        update_tier(): Updates the artist's tier based on their sales performance.
        __str__(): Returns a string representation of the artist (their legal name).
    """

    APPLICATION_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('LEGAL_REVIEW', 'Legal Review'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]

    TIER_CHOICES = (
        ('NEW', 'New'),
        ('EMERGING', 'Emerging'),
        ('POPULAR', 'Popular'),
        ('FAMOUS', 'Famous'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='artist_profile')
    legal_name = models.CharField(max_length=255)
    portfolio_url = models.URLField(blank=True)
    bio = models.TextField(blank=True)
    social_links = models.JSONField(blank=True, default=dict)
    artworks = models.ManyToManyField('Artwork', related_name='artists', blank=True)
    tier = models.ForeignKey(TierConfiguration, on_delete=models.SET_NULL, null=True, blank=True, related_name='artists', default=TierConfiguration.objects.get(tier='NEW').id)
    application_status = models.CharField(max_length=10, choices=APPLICATION_STATUS_CHOICES, default='PENDING')
    application_date = models.DateTimeField(auto_now_add=True)
    approval_date = models.DateTimeField(null=True, blank=True)
    commission = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_sales = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_commission = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    legal_documents = models.FileField(upload_to='artist_legal_documents', blank=True)
    tier_update_date = models.DateTimeField(null=True, blank=True)
    commission_wallet = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return self.legal_name

    def generate_referral_links(self):
        """Generates referral links for all artworks associated with the artist."""
        for artwork in self.artwork_set.all():
            referral_link, created = ReferralLink.objects.get_or_create(
                artist=self,
                product=artwork.saleor_product,
                defaults={'expires_at': timezone.now() + timezone.timedelta(days=7)}
            )
            if created:
                print(f"Generated referral link for {artwork.title}: {referral_link.code}")

    def get_referral_link_for_artwork(self, artwork):
        """Returns the referral link for a specific artwork."""
        return ReferralLink.objects.filter(artist=self, product=artwork.saleor_product).first()

    def get_total_referrals(self):
        """Returns the total number of referrals generated by the artist."""
        return self.referral_link_set.count()

    def get_total_referral_commissions(self):
        """Returns the total amount of commissions earned from referrals."""
        return self.referral_link_set.filter(used=True).aggregate(Sum('commission'))['commission__sum'] or 0

    def recalculate_total_sales(self):
        self.total_sales = self.user.orders.aggregate(Sum('total_gross_amount'))['total_gross_amount__sum'] or 0
        self.save()

class Artwork(models.Model):
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name='artwork_set')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='artist_artwork_images')
    is_available = models.BooleanField(default=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    dimensions = models.CharField(max_length=255, blank=True)
    saleor_product_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class ReferralLink(models.Model):
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    code = models.CharField(max_length=16, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    commission = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"Referral Link for {self.product.name} by {self.artist.legal_name}"

    def generate_code(self):
        """Generates a unique 16-character random code for the referral link."""
        while True:
            code = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(16))
            if not ReferralLink.objects.filter(code=code).exists():
                return code

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self.generate_code()
        super().save(*args, **kwargs)

    def is_valid(self):
        """Checks if the referral link is still valid."""
        return self.expires_at >= timezone.now() and not self.used

    def mark_as_used(self):
        """Marks the referral link as used."""
        self.used = True
        self.save()

@receiver(post_save, sender=Artwork)
def create_or_update_saleor_product(sender, instance, created, **kwargs):
    artwork_product_type, _ = ProductType.objects.get_or_create(name="Artwork")
    
    if created:
        product = Product.objects.create(
            name=instance.title,
            description=instance.description,
            product_type=artwork_product_type,
            is_published=instance.is_available
        )
        instance.saleor_product_id = product.id
        instance.save()

class Commission(models.Model):
    artist = models.ForeignKey(User, on_delete=models.CASCADE, related_name='commissions')
    order_line = models.ForeignKey(OrderLine, on_delete=models.CASCADE, related_name='commissions')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=(
        ('PENDING', 'Pending'),
        ('CREDITED', 'Credited'),
        ('PAID', 'Paid'),
        ('CANCELLED', 'Cancelled'),
    ), default='PENDING')

    def __str__(self):
        return f"Commission for {self.artist.username} - {self.amount}"

class CommissionSettings(models.Model):
    commission_period = models.PositiveIntegerField(default=14)
    referral_link_commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    product_type_commissions = models.JSONField(default=dict)  # Store as {product_type_id: rate}
    tier_commissions = models.JSONField(default=dict)  # Store as {tier_name: rate}
    tier_update_frequency = models.PositiveIntegerField(default=30, help_text="Number of days between tier updates")

    def __str__(self):
        return f"Commission Period: {self.commission_period} days"

class ReferralRate(models.Model):
    product_type = models.ForeignKey(ProductType, on_delete=models.CASCADE)
    rate = models.DecimalField(max_digits=5, decimal_places=2)

    def __str__(self):
        return f"{self.product_type.name} - {self.rate}%"

class CommissionRate(models.Model):
    name = models.CharField(max_length=255)
    rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    product_type = models.OneToOneField(ProductType, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.name