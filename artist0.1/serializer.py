from rest_framework import serializers
from .models import Artist, Artwork

class ArtistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Artist
        fields = ['id', 'legal_name', 'portfolio_url', 'bio', 'tier', 'application_status', 'total_sales']

class ArtworkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Artwork
        fields = ['id', 'title', 'description', 'image', 'price', 'is_available']