"""
VotoSecure URL Configuration
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Django admin (keep for superuser access)
    path('django-admin/', admin.site.urls),
    
    # Main apps
    path('', include('elections.urls')),
    path('accounts/', include('accounts.urls')),
    path('clubs/', include('clubs.urls')),
    path('dashboard/', include('dashboard.urls')),
]

# Serve static files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
