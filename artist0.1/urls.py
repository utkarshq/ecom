from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .api import ArtistViewSet, ArtworkViewSet, DashboardViewSet

router = DefaultRouter()
router.register(r'artists', ArtistViewSet)
router.register(r'artworks', ArtworkViewSet)
router.register(r'dashboard', DashboardViewSet, basename='dashboard')

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/', views.artist_dashboard, name='artist_dashboard'),
    path('approve/<int:artist_id>/', views.approve_artist, name='approve_artist'),
    path('reject/<int:artist_id>/', views.reject_artist, name='reject_artist'),
    path('sales-report/', views.sales_report, name='sales_report'),
    path('a/<str:username>/', views.artist_profile, name='artist_profile'),
    path('a/<slug:slug>/', views.artist_profile, name='artist_profile'),
    path('generate-referral/<int:product_id>/', views.generate_referral_link, name='generate_referral_link'),
    #... other URL patterns ...
]