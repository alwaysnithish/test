# Complete blog/urls.py - Copy this entire file

from django.urls import path
from . import views

urlpatterns = [
    # ==================== PUBLIC BLOG ====================
    path('', views.blog_list, name='blog_list'),
    path('category/<slug:slug>/', views.category_posts, name='category_posts'),
    path('tag/<slug:slug>/', views.tag_posts, name='tag_posts'),
    path('author/<str:username>/', views.author_profile, name='author_profile'),
    path('newsletter/subscribe/', views.newsletter_subscribe, name='newsletter_subscribe'),
    
    # ==================== AUTHENTICATION ====================
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Password Reset URLs
    path('password-reset/', views.CustomPasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', views.CustomPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', views.CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password-reset-complete/', views.CustomPasswordResetCompleteView.as_view(), name='password_reset_complete'),
    
    # ==================== DASHBOARD ====================
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/create/', views.create_post, name='create_post'),
    path('dashboard/edit/<slug:slug>/', views.edit_post, name='edit_post'),
    path('dashboard/delete/<slug:slug>/', views.delete_post, name='delete_post'),
    path('dashboard/profile/', views.edit_profile, name='edit_profile'),
    
    # ==================== BLOG DETAIL ====================
    # IMPORTANT: This MUST come LAST because it uses <slug:slug> pattern
    # which could conflict with other patterns
    path('<slug:slug>/', views.blog_detail, name='blog_detail'),
]
