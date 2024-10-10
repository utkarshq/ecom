from rest_framework import permissions

class IsArtistAdmin(permissions.BasePermission):
    """
    Custom permission to allow only staff users with the 'can_approve_artists' permission to access views.
    """

    def has_permission(self, request, view):
        return request.user.is_staff and request.user.has_perm('artist.can_approve_artists')

class IsArtist(permissions.BasePermission):
    """
    Custom permission to allow only artists to access views.
    """

    def has_permission(self, request, view):
        return request.user.is_active and request.user.has_perm('artist.is_artist')

class CanApproveArtists(permissions.BasePermission):
    """
    Custom permission to allow only users with the 'can_approve_artists' permission.
    """

    def has_permission(self, request, view):
        return request.user.has_perm('artist.can_approve_artists')

class CanRejectArtists(permissions.BasePermission):
    """
    Custom permission to allow only users with the 'can_reject_artists' permission.
    """

    def has_permission(self, request, view):
        return request.user.has_perm('artist.can_reject_artists')