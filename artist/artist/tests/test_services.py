from django.test import TestCase
from .factories import ArtistFactory, TierConfigurationFactory, ReferralLinkFactory
from .utils import create_artwork
from artist.services import CommissionCalculator, TierManager

class CommissionCalculatorTests(TestCase):
    def test_calculate_commission(self):
        artist = ArtistFactory()
        tier = TierConfigurationFactory(commission_rate=10)
        artist.tier = tier
        artist.save()
        order_line = OrderLine(unit_price=100)
        commission_calculator = CommissionCalculator()
        commission = commission_calculator.calculate_commission(order_line, artist)
        self.assertEqual(commission, 10)

    def test_calculate_tiered_commission(self):
        tier_bronze = TierConfigurationFactory(tier='Bronze', commission_rate=5, sales_threshold=100)
        tier_silver = TierConfigurationFactory(tier='Silver', commission_rate=10, sales_threshold=500, lower_tier=tier_bronze)
        tier_gold = TierConfigurationFactory(tier='Gold', commission_rate=15, sales_threshold=1000, lower_tier=tier_silver)
        artist1 = ArtistFactory(total_sales=50)
        artist2 = ArtistFactory(total_sales=200)
        artist3 = ArtistFactory(total_sales=700)
        artist1.tier = tier_bronze
        artist1.save()
        artist2.tier = tier_silver
        artist2.save()
        artist3.tier = tier_gold
        artist3.save()
        order_line = OrderLine(unit_price=100)
        commission_calculator = CommissionCalculator()
        commission1 = commission_calculator.calculate_tiered_commission(order_line, artist1)
        commission2 = commission_calculator.calculate_tiered_commission(order_line, artist2)
        commission3 = commission_calculator.calculate_tiered_commission(order_line, artist3)
        self.assertEqual(commission1, 5)
        self.assertEqual(commission2, 10)
        self.assertEqual(commission3, 15)

class TierManagerTests(TestCase):
    def test_get_tier_by_percentile(self):
        TierConfigurationFactory(tier='Bronze', percentile=20, commission_rate=5)
        TierConfigurationFactory(tier='Silver', percentile=50, commission_rate=10)
        TierConfigurationFactory(tier='Gold', percentile=80, commission_rate=15)
        TierConfigurationFactory(tier='Platinum', percentile=100, commission_rate=20)
        artist1 = ArtistFactory()
        artist2 = ArtistFactory()
        artist3 = ArtistFactory()
        tier_manager = TierManager()
        tier = tier_manager.get_tier(artist1)
        self.assertEqual(tier.tier, 'Bronze')
        tier = tier_manager.get_tier(artist2)
        self.assertEqual(tier.tier, 'Silver')
        tier = tier_manager.get_tier(artist3)
        self.assertEqual(tier.tier, 'Gold')

    def test_get_tier_by_sales_threshold(self):
        TierConfigurationFactory(tier='Bronze', sales_threshold=100, commission_rate=5)
        TierConfigurationFactory(tier='Silver', sales_threshold=500, commission_rate=10)
        TierConfigurationFactory(tier='Gold', sales_threshold=1000, commission_rate=15)
        TierConfigurationFactory(tier='Platinum', sales_threshold=5000, commission_rate=20)
        artist1 = ArtistFactory()
        artist2 = ArtistFactory()
        artist3 = ArtistFactory()
        artist1.total_sales = 150
        artist1.save()
        artist2.total_sales = 700
        artist2.save()
        artist3.total_sales = 1200
        artist3.save()
        tier_manager = TierManager()
        tier = tier_manager.get_tier(artist1)
        self.assertEqual(tier.tier, 'Silver')
        tier = tier_manager.get_tier(artist2)
        self.assertEqual(tier.tier, 'Gold')
        tier = tier_manager.get_tier(artist3)
        self.assertEqual(tier.tier, 'Platinum')

    def test_update_tier(self):
        # ... test logic ...