from rest_framework import permissions
from django.contrib.auth.models import Group


class IsCashierOrAdmin(permissions.BasePermission):
    """
    Custom permission to only allow cashiers and admins to access certain views.
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Check if user is in cashier or admin group or is staff
        return (
            request.user.groups.filter(name='cashier').exists() or
            request.user.groups.filter(name='admin').exists() or
            request.user.is_staff
        )


class IsAdminOnly(permissions.BasePermission):
    """
    Custom permission to only allow admins to access certain views.
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Check if user is in admin group or is staff
        return (
            request.user.groups.filter(name='admin').exists() or
            request.user.is_staff or
            request.user.is_superuser
        )


class IsRfidBridge(permissions.BasePermission):
    """
    Custom permission to allow RFID bridge access with token authentication.
    """
    
    def has_permission(self, request, view):
        from django.conf import settings
        
        # Check for bridge token in headers
        bridge_token = request.META.get('HTTP_X_BRIDGE_TOKEN')
        expected_token = settings.RFID_BRIDGE_TOKEN
        
        return bridge_token == expected_token


# Helper functions for template views
def is_cashier(user):
    """Check if user is a cashier."""
    return user.is_authenticated and user.groups.filter(name='cashier').exists()


def is_admin(user):
    """Check if user is an admin."""
    return user.is_authenticated and (user.is_superuser or user.groups.filter(name='admin').exists())

