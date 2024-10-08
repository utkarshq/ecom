from saleor.product.models import Product
from saleor.order.models import Order
from .models import Artist

def get_artist_products(artist: Artist) -> list[Product]:
    return list(Product.objects.filter(pk__in=artist.artwork_set.values('saleor_product_id')))

def get_artist_orders(artist: Artist) -> list[Order]:
    return list(Order.objects.filter(user=artist.user))