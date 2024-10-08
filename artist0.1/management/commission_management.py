from django.db import models
from django.contrib import admin
from artist.models import Artist, TierSettings

class CommissionRule(models.Model):
    SALE_TYPE_CHOICES = [
        ('REGULAR', 'Regular'),
        ('REFERRAL', 'Referral'),
        ('VOUCHER', 'Voucher'),
    ]

    sale_type = models.CharField(max_length=10, choices=SALE_TYPE_CHOICES)
    product_type = models.ForeignKey('product.ProductType', on_delete=models.CASCADE)
    artist_tier = models.ForeignKey(TierSettings, on_delete=models.CASCADE)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        unique_together = ('sale_type', 'product_type', 'artist_tier')

    def __str__(self):
        return f"{self.get_sale_type_display()} - {self.product_type} - {self.artist_tier}"

class CommissionRuleAdmin(admin.ModelAdmin):
    list_display = ('sale_type', 'product_type', 'artist_tier', 'commission_rate')
    list_filter = ('sale_type', 'product_type', 'artist_tier')
    search_fields = ('product_type__name', 'artist_tier__tier')

def calculate_commission(order_line, artist):
    product_type = order_line.product.product_type
    artist_tier = artist.tier
    sale_type = 'REFERRAL' if order_line.order.referral_code else 'REGULAR'
    
    applicable_rules = CommissionRule.objects.filter(
        sale_type__in=[sale_type, 'REGULAR'],
        product_type=product_type,
        artist_tier=artist_tier
    )
    
    if applicable_rules.exists():
        highest_rate = max(rule.commission_rate for rule in applicable_rules)
        return order_line.unit_price_gross * highest_rate / 100
    
    return 0  # Default to 0 if no rules apply