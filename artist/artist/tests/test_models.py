from django.test import TestCase
from .factories import ArtistFactory, TierConfigurationFactory, ReferralLinkFactory
from .utils import create_artwork

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