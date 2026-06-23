from rest_framework.authentication import SessionAuthentication


class CSRFExemptSessionAuthentication(SessionAuthentication):
    """
    Custom session authentication that doesn't require CSRF for local development.
    WARNING: Only use this in development environments!
    """
    
    def enforce_csrf(self, request):
        # Disable CSRF enforcement for API endpoints
        return None
