from django.apps import AppConfig


class ArtistConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'artist'

    def ready(self):
        from .permissions import create_all_permissions
        create_all_permissions()
'''
This file defines the ArtistConfig class, which is used to configure the Artist app.
It sets the default auto field to 'django.db.models.BigAutoField' and specifies the name of the app as 'artist'.
'''