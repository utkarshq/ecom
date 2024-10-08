from django import forms
from .models import Artist

class ArtistApplicationForm(forms.ModelForm):
    class Meta:
        model = Artist
        fields = ['legal_name', 'portfolio_url', 'bio', 'social_links']

class ArtistLegalDocumentsForm(forms.ModelForm):
    class Meta:
        model = Artist
        fields = ['legal_documents']
