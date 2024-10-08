from django.core.mail import send_mail
from django.conf import settings

def send_application_status_notification(artist):
    subject = f"Artist Application Status Update: {artist.application_status}"
    message = f"Dear {artist.legal_name},\n\nYour artist application status has been updated to: {artist.application_status}."
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [artist.user.email])

def send_commission_notification(artist, order):
    subject = f"New Commission for Order #{order.number}"
    message = f"Dear {artist.legal_name},\n\nYou have received a new commission for Order #{order.number}."
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [artist.user.email])