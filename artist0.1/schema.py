import graphene
from graphene_django import DjangoObjectType
from .models import Artist, TierSettings, CommissionRate, ReferralLink, Artwork, HistoricalCommissionRate
from .mutations import ArtistRegister, UpdateArtistProfile, CreateArtwork, UpdateArtwork, GenerateReferralLink, ApproveArtistApplication, RejectArtistApplication, RecalculateArtistSalesAndCommission
from django.db.models import Sum
from saleor.product.models import Product
from custom_order.models import CustomOrder

class ArtistType(DjangoObjectType):
    class Meta:
        model = Artist
        fields = ('id', 'legal_name', 'portfolio_url', 'bio', 'social_links', 'tier', 'application_status', 'total_sales', 'artworks', 'application_date', 'approval_date')

    total_commission = graphene.Decimal()
    referral_sales = graphene.Decimal()

    def resolve_total_commission(self, info):
        from .saleor_api import get_artist_orders, calculate_commission
        orders = get_artist_orders(self)
        return sum(calculate_commission(line, self) for order in orders for line in order.lines.all())

    def resolve_referral_sales(self, info):
        return CustomOrder.objects.filter(referral_link__artist=self).aggregate(total=Sum('order__total_gross_amount'))['total'] or 0

class TierSettingsType(DjangoObjectType):
    class Meta:
        model = TierSettings
        fields = '__all__'

class CommissionRateType(DjangoObjectType):
    class Meta:
        model = CommissionRate
        fields = '__all__'

class ReferralLinkType(DjangoObjectType):
    class Meta:
        model = ReferralLink
        fields = '__all__'

class ArtworkType(DjangoObjectType):
    class Meta:
        model = Artwork
        fields = '__all__'

class HistoricalCommissionRateType(DjangoObjectType):
    class Meta:
        model = HistoricalCommissionRate
        fields = '__all__'

class Query(graphene.ObjectType):
    artists = graphene.List(ArtistType, status=graphene.String())
    artist = graphene.Field(ArtistType, id=graphene.Int())
    tier_settings = graphene.List(TierSettingsType)
    commission_rates = graphene.List(CommissionRateType)
    referral_links = graphene.List(ReferralLinkType, artist_id=graphene.Int())
    artworks = graphene.List(ArtworkType, artist_id=graphene.Int())
    historical_commission_rates = graphene.List(HistoricalCommissionRateType, artist_id=graphene.Int())

    def resolve_artists(self, info, status=None):
        queryset = Artist.objects.all()
        if status:
            queryset = queryset.filter(application_status=status)
        return queryset

    def resolve_artist(self, info, id):
        return Artist.objects.get(pk=id)

    def resolve_tier_settings(self, info):
        return TierSettings.objects.all()

    def resolve_commission_rates(self, info):
        return CommissionRate.objects.all()

    def resolve_referral_links(self, info, artist_id=None):
        queryset = ReferralLink.objects.all()
        if artist_id:
            queryset = queryset.filter(artist_id=artist_id)
        return queryset

    def resolve_artworks(self, info, artist_id=None):
        queryset = Artwork.objects.all()
        if artist_id:
            queryset = queryset.filter(artist_id=artist_id)
        return queryset

    def resolve_historical_commission_rates(self, info, artist_id=None):
        queryset = HistoricalCommissionRate.objects.all()
        if artist_id:
            queryset = queryset.filter(artist_id=artist_id)
        return queryset

class Mutation(graphene.ObjectType):
    artist_register = ArtistRegister.Field()
    update_artist_profile = UpdateArtistProfile.Field()
    create_artwork = CreateArtwork.Field()
    update_artwork = UpdateArtwork.Field()
    generate_referral_link = GenerateReferralLink.Field()
    approve_artist_application = ApproveArtistApplication.Field()
    reject_artist_application = RejectArtistApplication.Field()
    recalculate_artist_sales_and_commission = RecalculateArtistSalesAndCommission.Field()

schema = graphene.Schema(query=Query, mutation=Mutation)
