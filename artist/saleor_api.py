from saleor.product.models import Product
from saleor.order.models import Order, OrderLine
from .models import CommissionRate, Artist, ReferralLink
from custom_order.models import CustomOrder

def get_artist_products(artist):
    return Product.objects.filter(attributes__values__name=artist.legal_name)

def get_artist_orders(artist):
    return Order.objects.filter(lines__variant__product__in=get_artist_products(artist))

def calculate_commission(order_line: OrderLine, artist: Artist) -> Decimal:
    product = order_line.variant.product
    product_type = product.product_type
    
    # Check if the order is from a referral
    try:
        referral_link = ReferralLink.objects.get(
            artist=artist,
            product=product,
            code=order_line.order.referral_code
        )
        is_referral = True
    except ReferralLink.DoesNotExist:
        is_referral = False

    # Get all applicable commission rates
    applicable_rates = [
        CommissionRate.objects.filter(product_type=product_type, is_referral=False).first(),
        CommissionRate.objects.filter(product_type=product_type, is_referral=True).first() if is_referral else None,
        artist.tier.commission_rate
    ]

    # Filter out None values and get the highest rate
    highest_rate = max(filter(None, applicable_rates), key=lambda x: x.rate if hasattr(x, 'rate') else x)

    if isinstance(highest_rate, CommissionRate):
        rate = highest_rate.rate
    else:
        rate = highest_rate

    return order_line.total_price_gross * (rate / Decimal('100'))

'''
This implementation does the following:
- It checks if the order is from a referral by looking for a matching ReferralLink.
- It collects all applicable commission rates: product type rate, referral rate (if applicable), and the artist's tier rate.
- It selects the highest rate among the applicable rates.
- It calculates the commission based on the highest rate.
'''