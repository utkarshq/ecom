class ArtistException(Exception):
    """Base exception for the Artist app"""
    pass

class ArtistNotFoundException(ArtistException):
    """Raised when an artist is not found"""
    pass

class InvalidCommissionRateError(ArtistException):
    """Raised when an invalid commission rate is provided"""
    pass

class TierConfigurationError(ArtistException):
    """Raised when there's an error with tier configuration"""
    pass