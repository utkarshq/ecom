from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from .models import Artist, ReferralLink
from .forms import ArtworkForm, ArtistApplicationForm, ArtistLegalDocumentsForm
from .utils import create_artwork, update_artwork
from .saleor_api import get_artist_products, get_artist_orders, calculate_commission
from saleor.product.models import Product
'''Implements the view functions for the Artist app, 
handling HTTP requests and responses, likely including artist-related operations and pages.'''


@login_required
def artwork_list(request):
    artist = get_object_or_404(Artist, user=request.user)
    artworks = get_artist_products(artist)
    return render(request, 'artist/artwork_list.html', {'artworks': artworks})

@login_required
def artwork_create(request):
    try:
        artist = request.user.artist_profile
    except Artist.DoesNotExist:
        raise PermissionDenied("You must be registered as an artist to create artwork listings.")
    
    if request.method == 'POST':
        form = ArtworkForm(request.POST, request.FILES)
        if form.is_valid():
            artwork = create_artwork(
                artist,
                form.cleaned_data['title'],
                form.cleaned_data['description'],
                form.cleaned_data['image'],
                form.cleaned_data['product_type_id'],
                form.cleaned_data['attributes']
            )
            return redirect('artwork_list')
    else:
        form = ArtworkForm()
    
    return render(request, 'artist/artwork_form.html', {'form': form})

@login_required
def artwork_update(request, pk):
    artwork = get_object_or_404(Product, pk=pk)
    artist_attribute = artwork.product_type.product_attributes.get(name='Artist')
    if artist_attribute.values.filter(name=request.user.artist_profile.legal_name).exists():
        raise PermissionDenied("You don't have permission to edit this artwork.")
    
    if request.method == 'POST':
        form = ArtworkForm(request.POST, request.FILES, instance=artwork)
        if form.is_valid():
            update_artwork(
                artwork.id,
                form.cleaned_data['title'],
                form.cleaned_data['description'],
                form.cleaned_data['image'],
                form.cleaned_data['attributes']
            )
            return redirect('artwork_list')
    else:
        form = ArtworkForm(instance=artwork)
    
    return render(request, 'artist/artwork_form.html', {'form': form})

@login_required
def apply_artist(request):
    if hasattr(request.user, 'artist_profile'):
        return redirect('artist_dashboard')

    if request.method == 'POST':
        form = ArtistApplicationForm(request.POST)
        if form.is_valid():
            artist = form.save(commit=False)
            artist.user = request.user
            artist.save()
            return redirect('artist_application_submitted')
    else:
        form = ArtistApplicationForm()

    return render(request, 'artist/apply.html', {'form': form})

@login_required
def artist_dashboard(request):
    artist = get_object_or_404(Artist, user=request.user)
    artworks = get_artist_products(artist)
    orders = get_artist_orders(artist)
    total_sales = sum(order.total_gross_amount for order in orders)
    total_commission = sum(calculate_commission(line, artist) for order in orders for line in order.lines.all())

    context = {
        'artist': artist,
        'artworks': artworks,
        'total_sales': total_sales,
        'total_commission': total_commission,
    }
    return render(request, 'artist/dashboard.html', context)

@login_required
def artist_application_status(request):
    artist = get_object_or_404(Artist, user=request.user)
    if artist.application_status == 'APPROVED':
        return redirect('artist_dashboard')

    if artist.application_status == 'PENDING' and not artist.legal_documents:
        if request.method == 'POST':
            form = ArtistLegalDocumentsForm(request.POST, request.FILES, instance=artist)
            if form.is_valid():
                form.save()
                return redirect('artist_application_status')
        else:
            form = ArtistLegalDocumentsForm()
        return render(request, 'artist/upload_legal_documents.html', {'form': form})

    return render(request, 'artist/application_status.html', {'artist': artist})

@login_required
def generate_referral_link(request, product_id):
    artist = get_object_or_404(Artist, user=request.user)
    product = get_object_or_404(Product, id=product_id)
    
    referral_link, created = ReferralLink.objects.get_or_create(artist=artist, product=product)
    
    return render(request, 'artist/referral_link.html', {'referral_link': referral_link})

"""
These views provide the following functionality:
1. artwork_list: Displays all artworks for the logged-in artist.
2. artwork_create: Allows artists to create new artwork listings.
3. artwork_update: Enables artists to update their existing artwork listings.

All views are protected with @login_required to ensure only authenticated users can access them.
Additional checks are in place to verify that the user is registered as an artist and has
permission to perform the requested actions.
"""
