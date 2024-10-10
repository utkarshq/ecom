from django.test import TestCase
from .factories import ArtistFactory, TierConfigurationFactory, ReferralLinkFactory, OrderFactory
from .utils import create_artwork
from ..services import CommissionCalculator, TierManager

class ArtistModelTests(TestCase):
    def test_update_tier(self):
        # ... test logic ...

class TierConfigurationModelTests(TestCase):
    def test_str_representation(self):
        # ... test logic ...

class ReferralLinkModelTests(TestCase):
    def test_is_valid(self):
        # ... test logic ...

    def test_str_representation(self):
        # ... test logic ...

class ArtworkModelTests(TestCase):
    def test_create_artwork(self):
        # ... test logic ...

class CommissionCalculationTests(TestCase):
    def setUp(self):
        self.artist = ArtistFactory()
        self.tier = TierConfigurationFactory(commission_rate=10)
        self.artist.tier = self.tier
        self.artist.save()
        self.order = OrderFactory(user=self.artist.user)
        self.commission_calculator = CommissionCalculator()

    def test_commission_calculation(self):
        commission = self.commission_calculator.calculate_commission(self.order.lines.first(), self.artist)
        expected_commission = self.order.lines.first().unit_price * Decimal('0.1')
        self.assertEqual(commission, expected_commission)

class TierUpdateTests(TestCase):
    def setUp(self):
        self.tier_manager = TierManager()
        self.artist = ArtistFactory(total_sales=Decimal('1000'))
        self.tier1 = TierConfigurationFactory(sales_threshold=Decimal('500'), commission_rate=5)
        self.tier2 = TierConfigurationFactory(sales_threshold=Decimal('1500'), commission_rate=10)

    def test_tier_update(self):
        self.tier_manager.update_tier(self.artist)
        self.assertEqual(self.artist.tier, self.tier1)
        
        self.artist.total_sales = Decimal('2000')
        self.artist.save()
        self.tier_manager.update_tier(self.artist)
        self.assertEqual(self.artist.tier, self.tier2)