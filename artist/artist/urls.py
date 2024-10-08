from django.urls import path
from . import views

app_name = 'artist'

urlpatterns = [
    path('', views.artwork_list, name='artwork_list'),
    path('<int:artwork_id>/', views.artwork_detail, name='artwork_detail'),
    path('generate_referral_link/<int:product_id>/', views.generate_referral_link, name='generate_referral_link'),
    # ... other URLs ...
]