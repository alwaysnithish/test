from django.urls import path
from . import views

urlpatterns = [
    # Authentication (Registration disabled)
    # path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Password Reset URLs
    path('password-reset/', views.CustomPasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', views.CustomPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', views.CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password-reset-complete/', views.CustomPasswordResetCompleteView.as_view(), name='password_reset_complete'),
    
    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/create/', views.create_post, name='create_post'),
    path('dashboard/edit/<slug:slug>/', views.edit_post, name='edit_post'),
    path('dashboard/delete/<slug:slug>/', views.delete_post, name='delete_post'),
    path('dashboard/profile/', views.edit_profile, name='edit_profile'),
    
    # Author Profile (Public)
    path('author/<str:username>/', views.author_profile, name='author_profile'),
    
    # Public Blog - IMPORTANT: Empty path MUST come BEFORE slug pattern!
    path('', views.blog_list, name='blog_list'),  # ← This FIRST
    path('<slug:slug>/', views.blog_detail, name='blog_detail'),  # ← This LAST
]
