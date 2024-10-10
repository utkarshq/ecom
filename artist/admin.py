from django.contrib import admin
from .models import Artist, TierConfiguration, ReferralLink, Commission, CommissionSettings
from .services import CommissionCalculator, TierManager, CommissionManager
from .notifications import send_application_status_notification
from .utils import log_action
from saleor.order.models import Order
from saleor.product.models import Product
from decimal import Decimal
from saleor.order.models import OrderLine
from django.utils import timezone
from django.db.models import Sum
from django.db import transaction

class BaseArtistAdminAction(admin.ModelAdmin):
    def has_change_permission(self, request, obj=None):
        return request.user.has_perm('artist.can_approve_artists') or request.user.has_perm('artist.can_reject_artists')

    def message_user(self, request, message, level='ERROR'):
        super().message_user(request, message, level=level)

@admin.register(Artist)
class ArtistAdmin(BaseArtistAdminAction):
    list_display = ('legal_name', 'tier', 'application_status', 'total_sales', 'total_commission')
    list_filter = ('tier', 'application_status')
    search_fields = ('legal_name', 'user__email')
    actions = ['approve_applications', 'reject_applications', 'recalculate_sales_and_commission', 'generate_referral_links', 'review_documents', 'final_approval', 'pay_artist_balance']

    @transaction.atomic
    def approve_applications(self, request, queryset):
        if not request.user.has_perm('artist.can_approve_artists'):
            self.message_user(request, "You don't have permission to approve artists.", level='ERROR')
            return
        try:
            updated = queryset.update(application_status='APPROVED')
            for artist in queryset:
                send_application_status_notification(artist)
                log_action(request.user, 'Approved application', 'Artist', artist.id)
            self.message_user(request, f"{updated} application(s) were successfully approved.", level='SUCCESS')
        except Exception as e:
            self.message_user(request, f"An error occurred: {str(e)}", level='ERROR')

    approve_applications.short_description = "Approve selected applications"

    def reject_applications(self, request, queryset):
        if not request.user.has_perm('artist.can_reject_artists'):
            self.message_user(request, "You don't have permission to reject artists.")
            return
        if queryset.filter(application_status='LEGAL_REVIEW').exists():
            self.message_user(request, "You can only reject artists whose application is under legal review.")
            return
        updated = queryset.update(application_status='REJECTED')
        for artist in queryset:
            log_action(request.user, 'Rejected application', 'Artist', artist.id)
        self.message_user(request, f"{updated} application(s) were successfully rejected.")
    reject_applications.short_description = "Reject selected applications"

    def recalculate_sales_and_commission(self, request, queryset):
        if not request.user.has_perm('artist.can_approve_artists'):
            self.message_user(request, "You don't have permission to recalculate sales and commission.")
            return
        for artist in queryset:
            artist.total_sales = artist.user.orders.aggregate(Sum('total_gross_amount'))['total_gross_amount__sum'] or 0
            artist.total_commission = artist.commissions.filter(status__in=['CREDITED', 'PAID']).aggregate(Sum('amount'))['amount__sum'] or 0
            artist.save()
            log_action(request.user, 'Recalculated sales and commission', 'Artist', artist.id)
    recalculate_sales_and_commission.short_description = "Recalculate sales and commission for selected artists"

    def generate_referral_links(self, request, queryset):
        if not request.user.has_perm('artist.can_approve_artists'):
            self.message_user(request, "You don't have permission to generate referral links.")
            return
        for artist in queryset:
            for artwork in artist.artwork_set.all():
                # Check if a referral link already exists
                if not ReferralLink.objects.filter(artist=artist, product=artwork.saleor_product).exists():
                    generate_referral_link(artist, artwork.saleor_product)
            log_action(request.user, 'Generated referral links', 'Artist', artist.id)
    generate_referral_links.short_description = "Generate referral links for selected artists"

    def review_documents(self, request, queryset):
        if not request.user.has_perm('artist.can_approve_artists'):
            self.message_user(request, "You don't have permission to mark applications for legal review.")
            return
        queryset.update(application_status='LEGAL_REVIEW')
        for artist in queryset:
            log_action(request.user, 'Marked for legal review', 'Artist', artist.id)
    review_documents.short_description = "Mark selected applications for legal review"

    def final_approval(self, request, queryset):
        if not request.user.has_perm('artist.can_approve_artists'):
            self.message_user(request, "You don't have permission to approve artists.")
            return
        queryset.update(application_status='APPROVED')
        for artist in queryset:
            send_application_status_notification(artist)
            log_action(request.user, 'Final approval', 'Artist', artist.id)
    final_approval.short_description = "Final approval for selected applications"

    @admin.action(description="Reset commission account for selected artists")
    def reset_commission_account(self, request, queryset):
        for artist in queryset:
            artist.commissions.filter(status='PAID').update(status='CANCELLED')
            artist.total_commission = Decimal(0)
            artist.save()

    def pay_artist_balance(self, request, queryset):
        if not request.user.has_perm('artist.can_manage_commissions'):
            self.message_user(request, "You don't have permission to pay artist balances.")
            return
        for artist in queryset:
            total_paid = CommissionManager.pay_artist_balance(artist)
            self.message_user(request, f"Paid ${total_paid} to {artist.legal_name}")
    pay_artist_balance.short_description = "Pay selected artists' balances"

@admin.register(TierConfiguration)
class TierConfigurationAdmin(admin.ModelAdmin):
    list_display = ('tier', 'percentile', 'commission_rate')

@admin.register(ReferralLink)
class ReferralLinkAdmin(admin.ModelAdmin):
    list_display = ('artist', 'product', 'code', 'created_at', 'expires_at', 'used')
    list_filter = ('artist', 'product')

@admin.register(Commission)
class CommissionAdmin(admin.ModelAdmin):
    list_display = ('artist', 'order_line', 'amount', 'created_at', 'paid_at', 'status')
    list_filter = ('status',)
    search_fields = ('artist__username', 'order_line__order__id')
    actions = ['credit_commission', 'cancel_commission']

    def credit_commission(self, request, queryset):
        if not request.user.has_perm('artist.can_manage_commissions'):
            self.message_user(request, "You don't have permission to credit commissions.")
            return
        for commission in queryset:
            if commission.status == 'PENDING':
                artist = commission.artist
                artist.commission_wallet += commission.amount
                artist.save()
                commission.status = 'CREDITED'
                commission.save()
                self.message_user(request, f"Commission {commission.id} has been credited to {artist.legal_name}'s wallet.")
            else:
                self.message_user(request, f"Commission {commission.id} is not in pending status.")
    credit_commission.short_description = "Credit selected commissions to artist's wallet"

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

class CommissionCalculator:
    def calculate_commission(self, order_line: OrderLine, artist: Artist) -> Decimal:
        product_type_commission = self.get_product_type_commission(order_line.product.product_type)
        referral_commission = self.get_referral_commission(order_line)
        tier_commission = self.get_tier_commission(artist)

        return max(product_type_commission, referral_commission, tier_commission)

    def get_product_type_commission(self, product_type: ProductType) -> Decimal:
        return product_type.commission_rate

    def get_referral_commission(self, order_line: OrderLine) -> Decimal:
        referral_link = ReferralLink.objects.filter(
            product=order_line.product,
            code__in=order_line.variant.metadata.get('referral_code', [])
        ).first()

        if referral_link:
            referral_rate = ReferralRate.objects.get(product_type=order_line.product.product_type)
            return referral_rate.rate
        return Decimal(0)

    def get_tier_commission(self, artist: Artist) -> Decimal:
        if artist.tier:
            return artist.tier.commission_rate
        return Decimal(0)

    def calculate_tiered_commission(self, order_line: OrderLine, artist: Artist) -> Decimal:
        tier = artist.tier
        if tier:
            if tier.sales_threshold:
                if artist.total_sales >= tier.sales_threshold:
                    return order_line.unit_price * tier.commission_rate / 100
                else:
                    return order_line.unit_price * tier.lower_tier.commission_rate / 100
            else:
                return order_line.unit_price * tier.commission_rate / 100
        return 0

    def get_sales_type_commission(self, order_line: OrderLine) -> Decimal:
        # Check if the order was placed using a referral link
        referral_link = ReferralLink.objects.filter(
            product=order_line.product,
            code__in=order_line.variant.metadata.get('referral_code', [])
        ).first()

        if referral_link:
            # Implement logic to retrieve the commission rate for referral links
            # ...
            return ...  # Return the referral link commission rate
        else:
            return None

class TierManager:
    # ... (previous code) ...

def generate_referral_link(artist: Artist, product: Product) -> ReferralLink:
    referral_link, created = ReferralLink.objects.get_or_create(
        artist=artist,
        product=product,
        defaults={'expires_at': timezone.now() + timezone.timedelta(days=7)}
    )
    return referral_link

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