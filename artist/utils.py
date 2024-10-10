from decimal import Decimal
from django.contrib.auth.models import User
from artist.models import Artist, ReferralLink, Artwork
from artist.services.commission import CommissionService
from saleor.order.models import Order, OrderLine
from saleor.product.models import Product
from django.utils import timezone
from django.contrib.admin.models import LogEntry
from django.contrib.contenttypes.models import ContentType

def get_artist_products(artist: Artist) -> list[Product]:
    return list(Product.objects.filter(pk__in=artist.artworks.values('saleor_product_id')))

def get_artist_orders(artist: Artist) -> list[Order]:
    return list(Order.objects.filter(user=artist.user))

def calculate_commission(order_line: OrderLine, artist: Artist) -> Decimal:
    commission_calculator = CommissionService()
    return commission_calculator.calculate_commission(order_line, artist)

def log_action(user: User, action: str, model_name: str, object_id: int, details: str = ''):
    content_type = ContentType.objects.get_for_model(Artist)
    LogEntry.objects.log_action(
        user_id=user.pk,
        content_type_id=content_type.pk,
        object_id=object_id,
        object_repr=f"Artist: {Artist.objects.get(id=object_id).legal_name}",
        action_flag=LogEntry.ACTION_FLAG_CHANGE,
        change_message=f"{action} - {details}"
    )

def create_artwork(artist: Artist, title: str, description: str, image: str, is_available: bool, dimensions: str) -> Artwork:
    artwork = Artwork.objects.create(
        artist=artist,
        title=title,
        description=description,
        image=image,
        is_available=is_available,
        dimensions=dimensions
    )
    return artwork

def update_artwork(artwork: Artwork, title: str, description: str, image: str, is_available: bool, price: Decimal, dimensions: str) -> Artwork:
    artwork.title = title
    artwork.description = description
    artwork.image = image
    artwork.is_available = is_available
    artwork.price = price
    artwork.dimensions = dimensions
    artwork.save()
    return artwork