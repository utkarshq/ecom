from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Artist
from .services import TierManager

@receiver(post_save, sender=Artist)
def update_artist_tier(sender, instance, created, **kwargs):
    if not created:
        tier_manager = TierManager()
        tier_manager.update_tier(instance)