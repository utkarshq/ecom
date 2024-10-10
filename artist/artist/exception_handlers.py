from django.http import JsonResponse
from .exceptions import ArtistNotFoundException, ArtworkNotFoundException, InvalidCommissionRateError

def artist_exception_handler(exc, context):
    if isinstance(exc, ArtistNotFoundException):
        return JsonResponse({'error': str(exc)}, status=404)
    elif isinstance(exc, ArtworkNotFoundException):
        return JsonResponse({'error': str(exc)}, status=404)
    elif isinstance(exc, InvalidCommissionRateError):
        return JsonResponse({'error': str(exc)}, status=400)
    return None