from django.contrib import admin
from .models import Artist, TierConfiguration, ReferralLink
from .services import CommissionCalculator, TierManager
from .notifications import send_application_status_notification
from .utils import log_action
from saleor.order.models import Order
from saleor.product.models import Product
from decimal import Decimal
from saleor.order.models import OrderLine
from django.utils import timezone
from django.db.models import Sum

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
        if not request.user.has_perm('artist.can_approve_artists'):
            self.message_user(request, "You don't have permission to recalculate sales and commission.")
            return
        for artist in queryset:
            commission_calculator = CommissionCalculator()
            artist.total_sales = artist.user.orders.aggregate(Sum('total_gross_amount'))['total_gross_amount__sum'] or 0
            artist.total_commission = 0
            for order in artist.user.orders.all():
                for order_line in order.lines.all():
                    artist.total_commission += commission_calculator.calculate_commission(order_line, artist)
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

@admin.register(TierConfiguration)
class TierConfigurationAdmin(admin.ModelAdmin):
    list_display = ('tier', 'percentile', 'commission_rate')

@admin.register(ReferralLink)
class ReferralLinkAdmin(admin.ModelAdmin):
    list_display = ('artist', 'product', 'code', 'created_at', 'expires_at', 'used')
    list_filter = ('artist', 'product')

class CommissionCalculator:
    def calculate_commission(self, order_line: OrderLine, artist: Artist) -> Decimal:
        tier = artist.tier
        if tier:
            return order_line.unit_price * tier.commission_rate / 100
        return 0

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