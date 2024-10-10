from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from .models import Artist, ReferralLink, Artwork, Commission
from .forms import ArtworkForm, ArtistApplicationForm, ArtistLegalDocumentsForm
from .utils import create_artwork, update_artwork, log_action
from .services import CommissionCalculator, TierService, ReferralLinkService
from saleor.product.models import Product
from django.http import HttpResponseServerError
from ..exceptions import ArtistNotFoundException, ArtworkNotFoundException, InvalidCommissionRateError
from django.utils.translation import gettext_lazy as _
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from ..dashboard_utils import get_dashboard_data
from django.contrib.auth.decorators import permission_required

@login_required
def artwork_list(request):
    try:
        artist = Artist.objects.get(user=request.user)
    except Artist.DoesNotExist:
        raise ArtistNotFoundException("Artist profile not found for this user.")
    artworks = artist.artwork_set.all()
    context = {
        'artist': artist,
        'artworks': artworks,
    }
    return render(request, 'artist/artwork_list.html', context)

@login_required
def artwork_detail(request, artwork_id):
    try:
        artist = Artist.objects.get(user=request.user)
    except Artist.DoesNotExist:
        raise ArtistNotFoundException("Artist profile not found for this user.")
    artwork = get_object_or_404(Artwork, pk=artwork_id)
    if artwork.artist != artist:
        raise PermissionDenied("You are not authorized to view this artwork.")
    referral_link = artist.get_referral_link_for_artwork(artwork)
    if referral_link:
        referral_link_url = f"{request.scheme}://{request.get_host()}/shop/products/{artwork.saleor_product.pk}/?referral_code={referral_link.code}"
    else:
        referral_link_url = None
    context = {
        'artist': artist,
        'artwork': artwork,
        'referral_link_url': referral_link_url,
    }
    return render(request, 'artist/artwork_detail.html', context)

@login_required
def artwork_create(request):
    try:
        artist = Artist.objects.get(user=request.user)
    except Artist.DoesNotExist:
        raise ArtistNotFoundException("Artist profile not found for this user.")
    if request.method == 'POST':
        form = ArtworkForm(request.POST, request.FILES)
        if form.is_valid():
            artwork = create_artwork(artist, form.cleaned_data)
            return redirect('artist:artwork_detail', artwork_id=artwork.id)
    else:
        form = ArtworkForm()
    context = {
        'artist': artist,
        'form': form,
    }
    return render(request, 'artist/artwork_create.html', context)

@login_required
def artwork_edit(request, artwork_id):
    try:
        artist = Artist.objects.get(user=request.user)
    except Artist.DoesNotExist:
        raise ArtistNotFoundException("Artist profile not found for this user.")
    artwork = get_object_or_404(Artwork, pk=artwork_id)
    if artwork.artist != artist:
        raise PermissionDenied("You are not authorized to edit this artwork.")
    if request.method == 'POST':
        form = ArtworkForm(request.POST, request.FILES, instance=artwork)
        if form.is_valid():
            update_artwork(artwork, form.cleaned_data)
            return redirect('artist:artwork_detail', artwork_id=artwork.id)
    else:
        form = ArtworkForm(instance=artwork)
    context = {
        'artist': artist,
        'artwork': artwork,
        'form': form,
    }
    return render(request, 'artist/artwork_edit.html', context)

@login_required
def artwork_delete(request, artwork_id):
    try:
        artist = Artist.objects.get(user=request.user)
    except Artist.DoesNotExist:
        raise ArtistNotFoundException("Artist profile not found for this user.")
    artwork = get_object_or_404(Artwork, pk=artwork_id)
    if artwork.artist != artist:
        raise PermissionDenied("You are not authorized to delete this artwork.")
    if request.method == 'POST':
        artwork.delete()
        return redirect('artist:artwork_list')
    context = {
        'artist': artist,
        'artwork': artwork,
    }
    return render(request, 'artist/artwork_delete.html', context)

@login_required
def artist_application(request):
    if request.user.is_artist:
        return redirect('artist:artwork_list')
    if request.method == 'POST':
        form = ArtistApplicationForm(request.POST)
        if form.is_valid():
            artist = form.save(commit=False)
            artist.user = request.user
            artist.save()
            return redirect('artist:artist_legal_documents')
    else:
        form = ArtistApplicationForm()
    context = {
        'form': form,
    }
    return render(request, 'artist/artist_application.html', context)

@login_required
def artist_legal_documents(request):
    try:
        artist = Artist.objects.get(user=request.user)
    except Artist.DoesNotExist:
        raise ArtistNotFoundException("Artist profile not found for this user.")
    if artist.application_status == 'APPROVED':
        return redirect('artist:artwork_list')
    if request.method == 'POST':
        form = ArtistLegalDocumentsForm(request.POST, request.FILES, instance=artist)
        if form.is_valid():
            form.save()
            artist.application_status = 'LEGAL_REVIEW'
            artist.save()
            return redirect('artist:artist_legal_documents_submitted')
    else:
        form = ArtistLegalDocumentsForm(instance=artist)
    context = {
        'artist': artist,
        'form': form,
    }
    return render(request, 'artist/artist_legal_documents.html', context)

@login_required
def artist_legal_documents_submitted(request):
    return render(request, 'artist/artist_legal_documents_submitted.html')

@permission_required('artist.can_approve_artists')
def admin_approve_artist(request, artist_id):
    artist = get_object_or_404(Artist, pk=artist_id)
    if artist.application_status != 'LEGAL_REVIEW':
        raise PermissionDenied("You can only approve artists whose application is under legal review.")

    artist.application_status = 'APPROVED'
    artist.save()
    send_application_status_notification(artist)
    log_action(request.user, 'Approved application', 'Artist', artist.id)
    return redirect('admin:artist_artist_changelist')

@permission_required('artist.can_reject_artists')
def admin_reject_artist(request, artist_id):
    artist = get_object_or_404(Artist, pk=artist_id)
    if artist.application_status != 'LEGAL_REVIEW':
        raise PermissionDenied("You can only reject artists whose application is under legal review.")

    artist.application_status = 'REJECTED'
    artist.save()
    send_application_status_notification(artist)
    log_action(request.user, 'Rejected application', 'Artist', artist.id)
    return redirect('admin:artist_artist_changelist')

@login_required
def sales_report(request):
    try:
        artist = Artist.objects.get(user=request.user)
    except Artist.DoesNotExist:
        raise ArtistNotFoundException("Artist profile not found for this user.")
    try:
        orders = artist.user.orders.annotate(month=TruncMonth('created_at')).values('month').annotate(total_sales=Sum('total_gross_amount')).order_by('month')
    except Exception as e:
        return HttpResponseServerError(f"An error occurred: {str(e)}")
    context = {
        'artist': artist,
        'orders': orders,
    }
    return render(request, 'artist/sales_report.html', context)

@permission_required('artist.can_approve_artists')
def artist_dashboard(request):
    dashboard_data = get_dashboard_data()
    context = {
        'dashboard_data': dashboard_data,
    }
    return render(request, 'artist/artist_dashboard.html', context)

@permission_required('artist.can_manage_commissions')

@permission_required('artist.can_manage_commissions')
def reset_artist_commissions(request, artist_id):
    artist = get_object_or_404(Artist, pk=artist_id)
    if request.method == 'POST':
        commissions = Commission.objects.filter(artist=artist)
        for commission in commissions:
            if commission.status == 'PAID':
                commission.status = 'CANCELLED'
                commission.paid_at = None
                commission.save()
                log_action(request.user, 'Reset commission', 'Commission', commission.id)
        return redirect('admin:artist_artist_changelist')

    context = {
        'artist': artist,
    }
    return render(request, 'artist/reset_artist_commissions.html', context)

@login_required
def commission_logs(request):
    try:
        artist = Artist.objects.get(user=request.user)
    except Artist.DoesNotExist:
        raise ArtistNotFoundException("Artist profile not found for this user.")

    commissions = Commission.objects.filter(artist=artist).order_by('-created_at')
    
    context = {
        'artist': artist,
        'commissions': commissions,
    }
    return render(request, 'artist/commission_logs.html', context)

@login_required
@permission_required('artist.can_view_commission_wallet', raise_exception=True)
def commission_wallet(request):
    try:
        artist = Artist.objects.get(user=request.user)
    except Artist.DoesNotExist:
        raise ArtistNotFoundException("Artist profile not found for this user.")
    
    context = {
        'artist': artist,
        'wallet_balance': artist.commission_wallet,
        'recent_commissions': Commission.objects.filter(artist=artist, status='CREDITED').order_by('-paid_at')[:10]
    }
    return render(request, 'artist/commission_wallet.html', context)