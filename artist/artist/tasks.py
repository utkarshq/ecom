from celery import shared_task
from .models import Artist
from ..services.tier import TierService
from .services import TierService

@shared_task
def update_artist_tiers():
    tier_service = TierService()
    artists = Artist.objects.all()
    for artist in artists:
        artist.recalculate_total_sales()
        tier_service.update_tier(artist)