from django.contrib import admin
from .models import Artist, TierSettings, CommissionRate
from .notifications import send_application_status_notification
from .saleor_api import get_artist_products, get_artist_orders, calculate_commission
from saleor.product.models import Product
from saleor.order.models import Order
'''
This file sets up the Django admin interface for the Artist app, 
registering models like Artist, TierSettings, and CommissionRate for admin management.
'''
@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    list_display = ('legal_name', 'tier', 'application_status', 'total_sales', 'total_commission')
    list_filter = ('tier', 'application_status')
    search_fields = ('legal_name', 'user__email')
    actions = ['approve_application', 'reject_application', 'recalculate_sales_and_commission', 'generate_referral_links']

    def approve_application(self, request, queryset):
        queryset.update(application_status='APPROVED')
        for artist in queryset:
            send_application_status_notification(artist)
    approve_application.short_description = "Approve selected applications"

    def reject_application(self, request, queryset):
        queryset.update(application_status='REJECTED')
        for artist in queryset:
            send_application_status_notification(artist)
    reject_application.short_description = "Reject selected applications"

    def recalculate_sales_and_commission(self, request, queryset):
        for artist in queryset:
            orders = get_artist_orders(artist)
            total_sales = sum(order.total_gross_amount for order in orders)
            total_commission = sum(calculate_commission(line, artist) for order in orders for line in order.lines.all())
            artist.total_sales = total_sales
            artist.total_commission = total_commission
            artist.save()
        self.message_user(request, f"Sales and commission recalculated for {queryset.count()} artists.")
    recalculate_sales_and_commission.short_description = "Recalculate sales and commission"

    def generate_referral_links(self, request, queryset):
        for artist in queryset:
            products = get_artist_products(artist)
            for product in products:
                ReferralLink.objects.get_or_create(artist=artist, product=product)
        self.message_user(request, f"Referral links generated for {queryset.count()} artists.")
    generate_referral_links.short_description = "Generate referral links for selected artists"

    def total_commission(self, obj):
        orders = get_artist_orders(obj)
        return sum(calculate_commission(line, obj) for order in orders for line in order.lines.all())
    total_commission.short_description = "Total Commission"

# The @admin.register decorator is a shortcut for admin.site.register(Artist, ArtistAdmin)
# It registers the Artist model with the custom ArtistAdmin configuration

"""
This admin configuration does the following:

1. It creates a custom admin interface for the Artist model.
2. It specifies which fields should be displayed in the list view, making it easy to see key information at a glance.
3. It adds filtering options for tier and approval status, allowing admins to quickly find specific groups of artists.
4. It enables searching by legal name and user email, making it easy to find specific artists.
5. It organizes the detail view into logical fieldsets, improving the layout and usability of the form.
6. It makes the application_date field read-only to prevent accidental modifications.

This configuration will make it easier for administrators to manage artists through the Django admin interface,
providing a user-friendly way to view, filter, search, and edit artist information.
"""

@admin.register(Artwork)
class ArtworkAdmin(admin.ModelAdmin):
    list_display = ('title', 'artist', 'price', 'is_available', 'created_at')
    list_filter = ('is_available', 'artist')
    search_fields = ('title', 'description', 'artist__legal_name')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Artwork Information', {
            'fields': ('artist', 'title', 'description', 'image', 'is_available')
        }),
        ('Admin-only Information', {
            'fields': ('price', 'dimensions'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

"""
This ArtworkAdmin configuration:
1. Displays key information in the list view for quick overview.
2. Provides filtering options for availability and artist.
3. Allows searching by title, description, and artist name.
4. Makes creation and update timestamps read-only to prevent accidental changes.
5. Organizes fields into logical groups, with admin-only information in a collapsible section.

This setup gives administrators an efficient way to manage artwork listings and control
sensitive information like pricing.
"""

@admin.register(TierSettings)
class TierSettingsAdmin(admin.ModelAdmin):
    list_display = ('tier', 'sales_threshold', 'commission_rate', 'use_percentile', 'percentile')
    list_filter = ('use_percentile',)

    def has_change_permission(self, request, obj=None):
        return request.user.has_perm('artist.change_tiersettings')

@admin.register(CommissionRate)
class CommissionRateAdmin(admin.ModelAdmin):
    list_display = ('product_type', 'commission_rate', 'is_referral')
    list_filter = ('is_referral',)

    def has_change_permission(self, request, obj=None):
        return request.user.has_perm('artist.change_commissionrate')

class ArtistInline(admin.StackedInline):
    model = Artist.artworks.through
    extra = 1

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    inlines = [ArtistInline]

    def has_change_permission(self, request, obj=None):
        return request.user.has_perm('product.change_product')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'created', 'status', 'total_gross_amount', 'is_referral')
    list_filter = ('status', 'is_referral')
    search_fields = ('id', 'user__email')

    def is_referral(self, obj):
        return getattr(obj, 'is_referral', False)
    is_referral.boolean = True
    is_referral.short_description = "Is Referral"
