from django.core.mail import send_mail
from .models import Artist

def send_application_status_notification(artist: Artist):
    subject = 'Your Artist Application Status'
    message = f'Dear {artist.legal_name},\n\nYour artist application has been updated. Your current status is: {artist.get_application_status_display()}.\n\nPlease log in to your account for more details.'
    from_email = 'noreply@yourdomain.com'
    recipient_list = [artist.user.email]
    send_mail(subject, message, from_email, recipient_list)
