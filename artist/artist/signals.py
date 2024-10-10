from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Artist
from .services import TierService

@receiver(post_save, sender=Artist)
def update_artist_tier(sender, instance, created, **kwargs):
    if not created:
        tier_service = TierService()
        tier_service.update_tier(instance)