from saleor.product.models import Product, ProductType, ProductVariant
from saleor.product.utils.attributes import associate_attribute_values_to_instance
from decimal import Decimal
from .models import Artist, CommissionRate

def create_artwork(artist, title, description, image, product_type_id, attribute_value_map):
    product_type = ProductType.objects.get(id=product_type_id)
    
    product = Product.objects.create(
        name=title,
        description=description,
        product_type=product_type,
    )
    
    # Associate the artist with the product (you might need to create a custom attribute for this)
    artist_attribute = product_type.product_attributes.get(name='Artist')
    associate_attribute_values_to_instance(product, artist_attribute, [artist.legal_name])
    
    # Associate other attributes
    for attribute, value in attribute_value_map.items():
        attr = product_type.product_attributes.get(name=attribute)
        associate_attribute_values_to_instance(product, attr, [value])
    
    # Create a default variant
    ProductVariant.objects.create(product=product, sku=f'ART-{product.id}')
    
    # Add the product image
    product.images.create(image=image, alt=title)
    
    return product

def update_artwork(product_id, title=None, description=None, image=None, attribute_value_map=None):
    product = Product.objects.get(id=product_id)
    
    if title:
        product.name = title
    if description:
        product.description = description
    
    product.save()
    
    if image:
        product.images.all().delete()
        product.images.create(image=image, alt=title or product.name)
    
    if attribute_value_map:
        for attribute, value in attribute_value_map.items():
            attr = product.product_type.product_attributes.get(name=attribute)
            associate_attribute_values_to_instance(product, attr, [value])
    
    return product

def calculate_commission(artist, product_type, sale_amount, is_referral=False):
    commission_rates = CommissionRate.objects.filter(
        tier=artist.tier,
        product_type=product_type,
        is_referral=is_referral
    ).order_by('-rate')

    if commission_rates.exists():
        rate = commission_rates.first().rate
    else:
        # Default rate if no specific rate is set
        rate = Decimal('0.10')

    return sale_amount * rate

def update_artist_tier(artist):
    if artist.total_sales >= Decimal('100000'):
        artist.tier = 'PLATINUM'
    elif artist.total_sales >= Decimal('50000'):
        artist.tier = 'GOLD'
    elif artist.total_sales >= Decimal('10000'):
        artist.tier = 'SILVER'
    else:
        artist.tier = 'NEW'
    artist.save()