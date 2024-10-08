import graphene
from django.core.exceptions import ValidationError
from django.utils import timezone
from saleor.graphql.core.mutations import ModelMutation
from saleor.graphql.account.types import User
from saleor.permission.enums import ProductPermissions, OrderPermissions, AccountPermissions
from saleor.core.permissions import get_permissions
from django.core.mail import send_mail
from django.conf import settings
from .models import Artist
from .types import ArtistType, ArtistInput

class ArtistRegister(ModelMutation):
    class Arguments:
        input = ArtistInput(required=True)

    class Meta:
        description = "Register a new artist."
        model = Artist
        object_type = ArtistType

    @classmethod
    def perform_mutation(cls, root, info, **data):
        user = info.context.user
        if not user.is_authenticated:
            raise ValidationError("You need to be logged in to register as an artist.")
        
        if hasattr(user, 'artist_profile'):
            raise ValidationError("You have already registered as an artist.")
        
        input_data = data.get("input", {})
        artist = Artist(
            user=user,
            legal_name=input_data.get("legal_name"),
            portfolio_url=input_data.get("portfolio_url"),
            bio=input_data.get("bio"),
            social_links=input_data.get("social_links"),
        )
        artist.save()
        
        cls.send_application_email(artist)
        
        return ArtistRegister(artist=artist)

    @staticmethod
    def send_application_email(artist):
        subject = "Artist Application Received"
        message = f"Dear {artist.legal_name},\n\nYour artist application has been received and is under review. We will notify you once a decision has been made.\n\nBest regards,\nThe Art Marketplace Team"
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [artist.user.email]
        send_mail(subject, message, from_email, recipient_list)

class ArtistApplicationAction(ModelMutation):
    class Arguments:
        id = graphene.ID(required=True, description="ID of the artist to approve or reject.")
        approve = graphene.Boolean(required=True, description="Whether to approve or reject the application.")

    class Meta:
        description = "Approve or reject an artist application."
        model = Artist
        object_type = ArtistType
        permissions = (AccountPermissions.MANAGE_STAFF,)

    @classmethod
    def perform_mutation(cls, root, info, id, approve):
        artist = cls.get_node_or_error(info, id, only_type=ArtistType)
        artist.is_approved = approve
        artist.approval_date = timezone.now() if approve else None
        artist.save()

        if approve:
            artist_permissions = [
                ProductPermissions.MANAGE_PRODUCTS,
                OrderPermissions.MANAGE_ORDERS,
            ]
            artist.user.user_permissions.add(*get_permissions(artist_permissions))

        cls.send_decision_email(artist, approve)

        return ArtistApplicationAction(artist=artist)

    @staticmethod
    def send_decision_email(artist, approved):
        subject = "Artist Application Update"
        if approved:
            message = f"Dear {artist.legal_name},\n\nCongratulations! Your artist application has been approved. You can now start listing your artwork on our platform.\n\nBest regards,\nThe Art Marketplace Team"
        else:
            message = f"Dear {artist.legal_name},\n\nWe regret to inform you that your artist application has not been approved at this time. If you have any questions, please contact our support team.\n\nBest regards,\nThe Art Marketplace Team"
        
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [artist.user.email]
        send_mail(subject, message, from_email, recipient_list)

class ArtistMutations(graphene.ObjectType):
    artist_register = ArtistRegister.Field()
    artist_application_action = ArtistApplicationAction.Field()