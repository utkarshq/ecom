class ArtistAppException(Exception):
    """Base exception for the artist app"""
    pass

class ArtistNotFoundException(ArtistAppException):
    """Raised when an artist is not found"""
    pass

class ArtworkNotFoundException(ArtistAppException):
    """Raised when an artwork is not found"""
    pass

class InvalidCommissionRateError(ArtistAppException):
    """Raised when there's an issue with commission rates"""
    pass