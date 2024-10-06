import graphene
from graphene_django import DjangoObjectType
from .models import Artist, TierSettings
from .types import ArtistType
from .mutations import ArtistMutations

class ArtistQueries(graphene.ObjectType):
    artist = graphene.Field(
        ArtistType,
        id=graphene.Argument(graphene.ID, description="ID of the artist.", required=True),
        description="Look up an artist by ID.",
    )
    all_artists = graphene.List(
        ArtistType,
        description="List of all artists.",
    )

    def resolve_artist(self, info, id):
        return Artist.objects.filter(pk=id).first()

    def resolve_all_artists(self, info):
        return Artist.objects.all()

class ArtistMutations(graphene.ObjectType):
    artist_register = ArtistMutations.ArtistRegister.Field()

class ArtistType(DjangoObjectType):
    class Meta:
        model = Artist
        fields = ('id', 'legal_name', 'portfolio_url', 'bio', 'social_links', 'tier', 'application_status', 'total_sales', 'artworks')

class TierSettingsType(DjangoObjectType):
    class Meta:
        model = TierSettings
        fields = ('id', 'tier', 'percentile', 'commission_rate')

class Query(graphene.ObjectType):
    artists = graphene.List(ArtistType)
    artist = graphene.Field(ArtistType, id=graphene.Int())
    tier_settings = graphene.List(TierSettingsType)

    def resolve_artists(self, info):
        return Artist.objects.filter(application_status='APPROVED')

    def resolve_artist(self, info, id):
        return Artist.objects.get(pk=id)

    def resolve_tier_settings(self, info):
        return TierSettings.objects.all()

schema = graphene.Schema(query=Query)