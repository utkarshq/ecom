from saleor.product.models import Product
from saleor.order.models import Order, OrderLine
from .models import CommissionRate, Artist, ReferralLink
from custom_order.models import CustomOrder
from django.core.cache import cache
from decimal import Decimal
from .management.commission_management import calculate_commission as calc_commission

def get_artist_products(artist):
    return Product.objects.filter(attributes__values__name=artist.legal_name)

def get_artist_orders(artist):
    return Order.objects.filter(lines__variant__product__in=get_artist_products(artist))

def calculate_commission(order_line: OrderLine, artist: Artist) -> Decimal:
    cache_key = f'commission_rate_{artist.id}_{order_line.id}'
    cached_rate = cache.get(cache_key)

    if cached_rate is not None:
        return cached_rate

    commission = calc_commission(order_line, artist)
    
    cache.set(cache_key, commission, timeout=3600)  # Cache for 1 hour

    return commission

'''
This implementation does the following:
- It checks if the order is from a referral by looking for a matching ReferralLink.
- It collects all applicable commission rates: product type rate, referral rate (if applicable), and the artist's tier rate.
- It selects the highest rate among the applicable rates.
- It calculates the commission based on the highest rate.
'''