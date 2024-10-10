from django.urls import path
from .artist import views

app_name = 'artist'

urlpatterns = [
    path('', views.artwork_list, name='artwork_list'),
    path('<int:artwork_id>/', views.artwork_detail, name='artwork_detail'),
    path('generate_referral_link/<int:product_id>/', views.generate_referral_link, name='generate_referral_link'),
    path('dashboard/', views.artist_dashboard, name='artist_dashboard'),
    path('application/', views.artist_application, name='artist_application'),
    path('application_status/', views.application_status, name='application_status'),
    path('upload_legal_documents/', views.upload_legal_documents, name='upload_legal_documents'),
    path('sales_report/', views.sales_report, name='sales_report'),
    path('commission_logs/', views.commission_logs, name='commission_logs'),
]