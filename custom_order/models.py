from django.db import models
from saleor.order.models import Order
from artist.models import ReferralLink

# Create your models here.
class CustomOrder(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='custom_order')
    referral_link = models.ForeignKey(ReferralLink, on_delete=models.SET_NULL, null=True, blank=True)

    @property
    def is_referral(self):
        return self.referral_link is not None

    def __str__(self):
        return f"Custom Order {self.order.id}"