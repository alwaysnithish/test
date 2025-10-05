from django.urls import path
from . import views

app_name = 'scanner'

urlpatterns = [
    path('qrscanner', views.home, name='home'),
    path('r/<str:scan_id>/', views.result, name='result'),
    path('a/<str:secret_code>/', views.analytics, name='analytics'),
]
