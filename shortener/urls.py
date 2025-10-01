from django.urls import path
from . import views

app_name = 'shortener'

urlpatterns = [
    path('urlshortener/', views.home, name='home'),
    path('<str:short_code>/', views.redirect_url, name='redirect'),
    path('a/<str:secret_code>/', views.analytics, name='analytics'),
    path('qr/<str:short_code>/', views.download_qr_code, name='download_qr'),
]
