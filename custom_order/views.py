from django.shortcuts import render, redirect, get_object_or_404
from saleor.checkout.utils import get_or_create_checkout_from_request
from .models import CustomOrder
from artist.models import ReferralLink

# Create your views here.

def custom_checkout(request, referral_code=None):
    checkout = get_or_create_checkout_from_request(request)
    
    if referral_code:
        referral_link = get_object_or_404(ReferralLink, code=referral_code)
        request.session['referral_code'] = str(referral_code)
    
    # Proceed with Saleor's normal checkout process
    # ...

    return render(request, 'checkout/index.html', {'checkout': checkout})

def create_custom_order(order):
    referral_code = order.checkout.get_referral_code()
    if referral_code:
        referral_link = ReferralLink.objects.get(code=referral_code)
        CustomOrder.objects.create(order=order, referral_link=referral_link)
    else:
        CustomOrder.objects.create(order=order)
