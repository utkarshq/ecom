from celery import shared_task
from .models import Artist
from .services import TierManager

@shared_task
def update_artist_tiers():
    artists = Artist.objects.all()
    tier_manager = TierManager()
    for artist in artists:
        tier_manager.update_tier(artist)