from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from saleor.product.models import ProductType
from django.db.models import Sum
from saleor.product.models import Product
from django.contrib.auth.models import User
import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from saleor.product.models import Product
'''
Contains the database models for the Artist app, 
likely including Artist, TierSettings, and CommissionRate models, 
which define the data structure for artists and related information.
'''

User = get_user_model()

class TierSettings(models.Model):
    TIER_CHOICES = [
        ('NEW', 'New'),
        ('SILVER', 'Silver'),
        ('GOLD', 'Gold'),
        ('PLATINUM', 'Platinum'),
    ]
    tier = models.CharField(max_length=10, choices=TIER_CHOICES, unique=True)
    sales_threshold = models.DecimalField(max_digits=10, decimal_places=2)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2)
    use_percentile = models.BooleanField(default=False)
    percentile = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"{self.tier} - {'Percentile' if self.use_percentile else 'Sales Threshold'}"

class CommissionRate(models.Model):
    product_type = models.ForeignKey(ProductType, on_delete=models.CASCADE)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2)
    is_referral = models.BooleanField(default=False)

    class Meta:
        unique_together = ('product_type', 'is_referral')

    def __str__(self):
        return f"{self.product_type} - {'Referral' if self.is_referral else 'Standard'}"

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

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='artist_profile')
    legal_name = models.CharField(max_length=255)
    portfolio_url = models.URLField()
    bio = models.TextField()
    social_links = models.JSONField(default=dict)
    tier = models.ForeignKey(TierSettings, on_delete=models.SET_NULL, null=True, blank=True)
    application_status = models.CharField(max_length=15, choices=APPLICATION_STATUS_CHOICES, default='PENDING')
    application_date = models.DateTimeField(auto_now_add=True)
    approval_date = models.DateTimeField(null=True, blank=True)
    total_sales = models.DecimalField(max_digits=10, decimal_places=2, default=0, db_index=True)
    legal_documents = models.FileField(upload_to='artist_legal_docs/', null=True, blank=True)
    contract_document = models.FileField(upload_to='artist_documents/', null=True, blank=True)
    identification_document = models.FileField(upload_to='artist_documents/', null=True, blank=True)
    bank_details_document = models.FileField(upload_to='artist_documents/', null=True, blank=True)

    def __str__(self):
        return self.legal_name

    def update_tier(self):
        """
        Updates the artist's tier based on their total sales in the last 365 days.

        This method calculates the total sales for the artist in the past year and
        assigns a tier based on predefined thresholds. It should be called periodically
        or after significant sales events to keep the tier status current.

        The tier thresholds are:
        - NEW: Less than $10,000 in sales
        - SILVER: $10,000 - $49,999 in sales
        - GOLD: $50,000 - $99,999 in sales
        - PLATINUM: $100,000 or more in sales

        Note: This method assumes that the TierSettings model has been properly configured
        with the correct tier thresholds.
        """
        # Calculate total sales in the last 365 days
        one_year_ago = timezone.now() - timezone.timedelta(days=365)
        total_sales = self.user.orders.filter(created_at__gte=one_year_ago).aggregate(
            total=Sum('total_gross_amount')
        )['total'] or 0

        if total_sales >= 100000:  # $100,000
            self.tier = 'PLATINUM'
        elif total_sales >= 50000:  # $50,000
            self.tier = 'GOLD'
        elif total_sales >= 10000:  # $10,000
            self.tier = 'SILVER'
        else:
            self.tier = 'NEW'
        
        self.save()

"""
This Artist model represents an artist in our marketplace. It includes:

1. Basic information fields like legal name, portfolio URL, and bio.
2. A JSON field for social links, allowing flexible storage of multiple social media profiles.
3. A tier system to categorize artists based on their sales performance.
4. Approval status and related dates for the application process.
5. New fields for storing verification documents (contract, identification, and bank details).
6. A method to update the artist's tier based on their sales performance.

The new document fields use FileField to store uploaded documents. They are set to null=True and blank=True
to make them optional in forms and the database, allowing for a gradual verification process.

The update_tier method calculates the artist's total sales over the past year and updates their tier accordingly.
This method should be called periodically or after each sale to keep the tier up-to-date.
"""

class Artwork(models.Model):
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name='artworks')
    title = models.CharField(max_length=255)
    description = models.TextField()
    image = models.ImageField(upload_to='artworks/')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_available = models.BooleanField(default=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    dimensions = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return self.title

"""
The Artwork model represents individual artworks listed by artists. It includes:
1. A foreign key to the Artist model to associate each artwork with its creator.
2. Basic information fields like title, description, and an image of the artwork.
3. Timestamps for creation and last update.
4. An availability flag to easily mark artworks as sold or unavailable.
5. Price and dimensions fields that can only be set by administrators.

This model allows artists to upload and manage their artwork listings, while giving
administrators control over pricing and dimension information.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from saleor.product.models import ProductType

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
    else:
        product = Product.objects.get(name=instance.title)
        product.description = instance.description
        product.is_published = instance.is_available
        product.save()

    # Update price if set
    if instance.price:
        product.variants.update_or_create(
            sku=f"ART-{instance.id}",
            defaults={"price_amount": instance.price}
        )

class CommissionRate(models.Model):
    tier = models.CharField(max_length=10, choices=Artist.TIER_CHOICES)
    product_type = models.ForeignKey('product.ProductType', on_delete=models.CASCADE)
    rate = models.DecimalField(max_digits=4, decimal_places=2)
    is_referral = models.BooleanField(default=False)

    class Meta:
        unique_together = ('tier', 'product_type', 'is_referral')

    def __str__(self):
        return f"{self.tier} - {self.product_type} - {'Referral' if self.is_referral else 'Normal'}"

class TierSettings(models.Model):
    tier = models.CharField(max_length=10, choices=Artist.TIER_CHOICES, unique=True)
    percentile = models.DecimalField(max_digits=5, decimal_places=2)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2)

    def __str__(self):
        return f"{self.tier} - {self.percentile}% - {self.commission_rate}%"


User = get_user_model()

class ReferralLink(models.Model):
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE)
    product = models.ForeignKey('product.Product', on_delete=models.CASCADE)
    code = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(days=7)
        super().save(*args, **kwargs)

    @property
    def is_valid(self):
        return timezone.now() < self.expires_at

class HistoricalCommissionRate(models.Model):
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE)
    rate = models.DecimalField(max_digits=5, decimal_places=2)
    effective_from = models.DateTimeField()
    effective_to = models.DateTimeField(null=True, blank=True)

    class Meta:
        get_latest_by = 'effective_from'

class TierConfiguration(models.Model):
    use_percentile = models.BooleanField(default=False)
    new_threshold = models.DecimalField(max_digits=10, decimal_places=2)
    silver_threshold = models.DecimalField(max_digits=10, decimal_places=2)
    gold_threshold = models.DecimalField(max_digits=10, decimal_places=2)
    platinum_threshold = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Tier Configuration ({'Percentile' if self.use_percentile else 'Sales'})"

### Audit Log ###

class AuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=255)
    model_name = models.CharField(max_length=100)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    details = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.action} - {self.timestamp}"

    class Meta:
        ordering = ['-timestamp']