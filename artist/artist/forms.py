from django import forms
from .models import Artist, Artwork, TierConfiguration
from django.utils.translation import gettext_lazy as _
from saleor.product.models import Product
from django.core.validators import MinValueValidator

class ArtistApplicationForm(forms.ModelForm):
    class Meta:
        model = Artist
        fields = ['legal_name', 'portfolio_url', 'bio', 'social_links']

class ArtistLegalDocumentsForm(forms.ModelForm):
    class Meta:
        model = Artist
        fields = ['legal_documents']

class ArtworkForm(forms.ModelForm):
    class Meta:
        model = Artwork
        fields = ['title', 'description', 'image', 'is_available', 'price', 'dimensions']

class TierConfigurationForm(forms.ModelForm):
    class Meta:
        model = TierConfiguration
        fields = ['tier', 'use_percentile', 'percentile', 'sales_threshold', 'commission_rate']

    def clean(self):
        cleaned_data = super().clean()
        use_percentile = cleaned_data.get('use_percentile')
        percentile = cleaned_data.get('percentile')
        sales_threshold = cleaned_data.get('sales_threshold')

        if use_percentile and sales_threshold is not None:
            raise forms.ValidationError(_("You can't set both percentile and sales threshold."))
        if not use_percentile and percentile is not None:
            raise forms.ValidationError(_("You can't set percentile without enabling 'Use Percentile'."))

        return cleaned_data
