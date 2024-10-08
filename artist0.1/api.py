from rest_framework import viewsets
from .models import Artist, Artwork
from .serializers import ArtistSerializer, ArtworkSerializer
from .dashboard_utils import get_dashboard_data

class ArtistViewSet(viewsets.ModelViewSet):
    queryset = Artist.objects.all()
    serializer_class = ArtistSerializer

class ArtworkViewSet(viewsets.ModelViewSet):
    queryset = Artwork.objects.all()
    serializer_class = ArtworkSerializer

class DashboardViewSet(viewsets.ViewSet):
    def list(self, request):
        artist = request.user.artist_profile
        dashboard_data = get_dashboard_data(artist)
        return Response(dashboard_data)