from artist.models import Artist, Commission, ReferralLink
from saleor.order.models import Order
from django.db.models import Sum, Count, Avg, F
from django.db.models.functions import TruncMonth
from django.utils import timezone
from .dashboard_data import ArtistDashboardData, AdminDashboardData

def get_artist_dashboard_data(artist):
    """Fetches and structures data for the artist dashboard."""
    total_sales = artist.user.orders.aggregate(total_sales=Sum('total_gross_amount'))['total_sales'] or 0
    this_month_sales = artist.user.orders.filter(created_at__month=timezone.now().month).aggregate(total_sales=Sum('total_gross_amount'))['total_sales'] or 0
    total_commissions = Commission.objects.filter(artist=artist).aggregate(total_commissions=Sum('amount'))['total_commissions'] or 0
    pending_commissions = Commission.objects.filter(artist=artist, status='PENDING').aggregate(total_commissions=Sum('amount'))['total_commissions'] or 0
    available_for_payout = Commission.objects.filter(artist=artist, status='CREDITED').aggregate(total_commissions=Sum('amount'))['total_commissions'] or 0
    referral_links = ReferralLink.objects.filter(artist=artist).count()

    return ArtistDashboardData(
        total_sales=total_sales,
        this_month_sales=this_month_sales,
        total_commissions=total_commissions,
        pending_commissions=pending_commissions,
        available_for_payout=available_for_payout,
        referral_links=referral_links,
    )

def get_admin_dashboard_data():
    """Fetches and structures data for the admin dashboard."""
    total_artists = Artist.objects.count()
    total_sales = Order.objects.aggregate(total_sales=Sum('total_gross_amount'))['total_sales'] or 0
    total_commissions_paid = Commission.objects.filter(status='PAID').aggregate(total_commissions=Sum('amount'))['total_commissions'] or 0
    monthly_sales = Order.objects.annotate(month=TruncMonth('created_at')).values('month').annotate(total_sales=Sum('total_gross_amount')).order_by('month')

    return AdminDashboardData(
        total_artists=total_artists,
        total_sales=total_sales,
        total_commissions_paid=total_commissions_paid,
        monthly_sales=monthly_sales,
    )