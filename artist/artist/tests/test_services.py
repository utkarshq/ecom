from django.test import TestCase
from ..models import Artist, TierConfiguration
from ..services.commission import CommissionService
from ..services.tier import TierService
from .factories import ArtistFactory, TierConfigurationFactory, OrderLineFactory

class CommissionServiceTests(TestCase):
    def setUp(self):
        self.commission_service = CommissionService()

    def test_calculate_commission(self):
        artist = ArtistFactory()
        order_line = OrderLineFactory()
        commission = self.commission_service.calculate_commission(order_line, artist)
        self.assertIsInstance(commission, Decimal)

class TierServiceTests(TestCase):
    def setUp(self):
        self.tier_service = TierService()

    def test_get_tier(self):
        artist = ArtistFactory()
        tier = self.tier_service.get_tier(artist)
        self.assertIsInstance(tier, TierConfiguration)

    def test_update_tier(self):
        artist = ArtistFactory()
        old_tier = artist.tier
        self.tier_service.update_tier(artist)
        self.assertNotEqual(old_tier, artist.tier)