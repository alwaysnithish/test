"""
URL configuration for fileconverter app.
"""
from django.urls import path
from . import views

app_name = 'fileconverter'

urlpatterns = [
    path('', views.home, name='home'),
    path('convert/', views.convert_file, name='convert'),
    path('download/<str:filename>/', views.download_file, name='download'),
]
