#from django.contrib import admin
"""from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('tools21k.urls')),
    path('video/', include('videodownloader.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('',views.home,name='home'),
    path('download/', include('videodownloader.urls')),  # Include app URLs at root
    path('convert/',include('fileconverter.urls')),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)