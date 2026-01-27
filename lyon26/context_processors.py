import os


def admin_username(request):
    """Add DJANGO_SUPERUSER_USERNAME to template context."""
    return {
        'ADMIN_USERNAME': os.environ.get('DJANGO_SUPERUSER_USERNAME', '')
    }
