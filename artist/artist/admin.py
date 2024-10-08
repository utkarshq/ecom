from django.contrib import admin
from .models import Artist, TierConfiguration, ReferralLink, Commission, CommissionSettings
from saleor.order.models import OrderLine
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from .dashboard_utils import get_dashboard_data
from django.contrib.auth.decorators import permission_required
from django.shortcuts import render, redirect, get_object_or_404
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from .forms import ArtworkForm, ArtistApplicationForm, ArtistLegalDocumentsForm
from .utils import create_artwork, update_artwork, log_action
from .services import CommissionCalculator, TierManager, generate_referral_link
from saleor.product.models import Product
from django.http import HttpResponseServerError
from .exceptions import ArtistNotFoundException, ArtworkNotFoundException, InvalidCommissionRateError
from django.utils.translation import gettext_lazy as _
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from .dashboard_utils import get_dashboard_data
from django.contrib.auth.decorators import permission_required

User = get_user_model()

@admin.register(Artist)
class ArtistAdmin(BaseArtistAdminAction):
    list_display = ('legal_name', 'tier', 'application_status', 'total_sales', 'total_commission')
    list_filter = ('tier', 'application_status')
    search_fields = ('legal_name', 'user__email')
    actions = ['approve_application', 'reject_application', 'recalculate_sales_and_commission', 'generate_referral_links', 'review_documents', 'final_approval']

    def approve_application(self, request, queryset):
        if not request.user.has_perm('artist.can_approve_artists'):
            self.message_user(request, "You don't have permission to approve artists.")
            return
        queryset.update(application_status='APPROVED')
        for artist in queryset:
            send_application_status_notification(artist)
            log_action(request.user, 'Approved application', 'Artist', artist.id)
    approve_application.short_description = "Approve selected applications"

    def reject_application(self, request, queryset):
        if not request.user.has_perm('artist.can_reject_artists'):
            self.message_user(request, "You don't have permission to reject artists.")
            return
        if any(artist.application_status == 'LEGAL_REVIEW' for artist in queryset):
            self.message_user(request, "You can only reject artists whose application is under legal review.")
            return
        queryset.update(application_status='REJECTED')
        for artist in queryset:
            log_action(request.user, 'Rejected application', 'Artist', artist.id)
    reject_application.short_description = "Reject selected applications"

    def recalculate_sales_and_commission(self, request, queryset):
        if not request.user.has_perm('artist.can_manage_commissions'):
            self.message_user(request, "You don't have permission to recalculate sales and commissions.")
            return
        for artist in queryset:
            artist.total_sales = artist.user.orders.aggregate(Sum('total_gross_amount'))['total_gross_amount__sum'] or 0
            artist.total_commission = artist.user.commissions.filter(status='PAID').aggregate(Sum('amount'))['amount__sum'] or 0
            artist.save()
            self.message_user(request, f"Sales and commissions recalculated for {artist.legal_name}")
    recalculate_sales_and_commission.short_description = "Recalculate sales and commissions"

    def generate_referral_links(self, request, queryset):
        if not request.user.has_perm('artist.can_manage_commissions'):
            self.message_user(request, "You don't have permission to generate referral links.")
            return
        for artist in queryset:
            for artwork in artist.artwork.all():
                generate_referral_link(artist, artwork.saleor_product)
                self.message_user(request, f"Referral links generated for {artist.legal_name}")
    generate_referral_links.short_description = "Generate referral links"

    def review_documents(self, request, queryset):
        if not request.user.has_perm('artist.can_review_documents'):
            self.message_user(request, "You don't have permission to review documents.")
            return
        queryset.update(application_status='LEGAL_REVIEW')
        for artist in queryset:
            log_action(request.user, 'Started legal document review', 'Artist', artist.id)
    review_documents.short_description = "Start legal document review"

    def final_approval(self, request, queryset):
        if not request.user.has_perm('artist.can_approve_artists'):
            self.message_user(request, "You don't have permission to approve artists.")
            return
        queryset.update(application_status='APPROVED')
        for artist in queryset:
            log_action(request.user, 'Approved application', 'Artist', artist.id)
    final_approval.short_description = "Final approval"

@admin.register(TierConfiguration)
class TierConfigurationAdmin(admin.ModelAdmin):
    list_display = ('tier', 'percentile', 'commission_rate')

@admin.register(ReferralLink)
class ReferralLinkAdmin(admin.ModelAdmin):
    list_display = ('artist', 'product', 'code', 'created_at', 'expires_at', 'used')

@admin.register(Commission)
class CommissionAdmin(admin.ModelAdmin):
    list_display = ('artist', 'order_line', 'amount', 'created_at', 'paid_at', 'status')
    list_filter = ('status',)
    search_fields = ('artist__username', 'order_line__order__id')
    actions = ['pay_commission', 'cancel_commission']

    def pay_commission(self, request, queryset):
        if not request.user.has_perm('artist.can_manage_commissions'):
            self.message_user(request, "You don't have permission to pay commissions.")
            return
        for commission in queryset:
            if commission.status == 'PENDING':
                commission.status = 'PAID'
                commission.paid_at = timezone.now()
                commission.save()
                log_action(request.user, 'Paid commission', 'Commission', commission.id)
            else:
                self.message_user(request, f"Commission {commission.id} is not in pending status.")
    pay_commission.short_description = "Pay selected commissions"

    def cancel_commission(self, request, queryset):
        if not request.user.has_perm('artist.can_manage_commissions'):
            self.message_user(request, "You don't have permission to cancel commissions.")
            return
        for commission in queryset:
            if commission.status == 'PENDING':
                commission.status = 'CANCELLED'
                commission.save()
                log_action(request.user, 'Cancelled commission', 'Commission', commission.id)
            else:
                self.message_user(request, f"Commission {commission.id} is not in pending status.")
    cancel_commission.short_description = "Cancel selected commissions"

@admin.register(CommissionSettings)
class CommissionSettingsAdmin(admin.ModelAdmin):
    list_display = ('commission_period', 'referral_link_commission_rate')
    fieldsets = (
        (None, {
            'fields': ('commission_period', 'referral_link_commission_rate')
        }),
        ('Product Type Commissions', {
            'fields': ('product_type_commissions',)
        }),
        ('Tier Commissions', {
            'fields': ('tier_commissions',)
        }),
    )