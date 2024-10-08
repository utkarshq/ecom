import graphene
from graphene_django import DjangoObjectType
from .models import Artist

class ArtistType(DjangoObjectType):
    class Meta:
        model = Artist
        fields = ('id', 'legal_name', 'portfolio_url', 'bio', 'social_links', 'tier', 'is_approved', 'application_date', 'approval_date')

class ArtistInput(graphene.InputObjectType):
    legal_name = graphene.String(required=True)
    portfolio_url = graphene.String(required=True)
    bio = graphene.String(required=True)
    social_links = graphene.JSONString(required=True)