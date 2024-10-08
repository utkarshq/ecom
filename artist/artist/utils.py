from django.contrib.auth.models import User
from .models import Artist, ReferralLink, Artwork
from .services import CommissionCalculator, TierManager
from saleor.order.models import Order
from saleor.product.models import Product
from django.utils import timezone

def get_artist_products(artist: Artist) -> list[Product]:
    return list(Product.objects.filter(pk__in=artist.artwork_set.values('saleor_product_id')))

def get_artist_orders(artist: Artist) -> list[Order]:
    return list(Order.objects.filter(user=artist.user))

def calculate_commission(order_line: OrderLine, artist: Artist) -> Decimal:
    commission_calculator = CommissionCalculator()
    return commission_calculator.calculate_commission(order_line, artist)

def log_action(user: User, action: str, model_name: str, object_id: int, details: str = ''):
    # ... logic for logging actions ...

def create_artwork(artist: Artist, title: str, description: str, image: str, is_available: bool, price: Decimal, dimensions: str) -> Artwork:
    # ... logic for creating artwork ...

def update_artwork(artwork: Artwork, title: str, description: str, image: str, is_available: bool, price: Decimal, dimensions: str) -> Artwork:
    # ... logic for updating artwork ...