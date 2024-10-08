from django.test import TestCase

# Create your tests here.
from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Artist, Artwork, TierSettings, CommissionRate
from .views import generate_referral_link
from django.urls import reverse
from graphene_django.utils.testing import GraphQLTestCase

User = get_user_model()

class ArtistModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testartist', password='12345')
        self.artist = Artist.objects.create(
            user=self.user,
            legal_name='Test Artist',
            portfolio_url='http://test.com',
            bio='Test bio'
        )

    def test_artist_creation(self):
        self.assertTrue(isinstance(self.artist, Artist))
        self.assertEqual(self.artist.__str__(), self.artist.legal_name)

    def test_update_tier(self):
        TierSettings.objects.create(tier='NEW', percentile=0, commission_rate=10)
        TierSettings.objects.create(tier='SILVER', percentile=25, commission_rate=15)
        self.artist.update_tier()
        self.assertEqual(self.artist.tier.tier, 'NEW')

class ArtworkModelTest(TestCase):
    def setUp(self):
        user = User.objects.create_user(username='testartist', password='12345')
        self.artist = Artist.objects.create(user=user, legal_name='Test Artist')
        self.artwork = Artwork.objects.create(
            artist=self.artist,
            title='Test Artwork',
            description='Test description',
            price=100.00
        )

    def test_artwork_creation(self):
        self.assertTrue(isinstance(self.artwork, Artwork))
        self.assertEqual(self.artwork.__str__(), self.artwork.title)

class ArtistViewsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testartist', password='12345')
        self.artist = Artist.objects.create(user=self.user, legal_name='Test Artist')
        self.client.login(username='testartist', password='12345')

    def test_generate_referral_link(self):
        artwork = Artwork.objects.create(artist=self.artist, title='Test Artwork')
        response = self.client.get(reverse('generate_referral_link', args=[artwork.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'referral_link')

class ArtistGraphQLTest(GraphQLTestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testartist', password='12345')
        self.artist = Artist.objects.create(user=self.user, legal_name='Test Artist')

    def test_artist_query(self):
        response = self.query(
            '''
            query {
                artists {
                    edges {
                        node {
                            legalName
                        }
                    }
                }
            }
            '''
        )
        self.assertResponseNoErrors(response)
        self.assertEqual(response.json()['data']['artists']['edges'][0]['node']['legalName'], 'Test Artist')