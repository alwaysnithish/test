# Complete blog/views.py - Copy this entire file

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from django.http import JsonResponse
from django.contrib.auth.models import User
from .models import BlogPost, Category, Tag, AuthorProfile
from .forms import BlogPostForm, AuthorProfileForm
import json

# Import password reset views
from django.contrib.auth.views import (
    PasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView
)
from django.urls import reverse_lazy


# Helper function - must be defined before use
def is_admin(user):
    return user.is_staff or user.is_superuser


# Custom Password Reset Views
class CustomPasswordResetView(PasswordResetView):
    template_name = 'blog/password_reset.html'
    email_template_name = 'blog/password_reset_email.html'
    subject_template_name = 'blog/password_reset_subject.txt'
    success_url = reverse_lazy('password_reset_done')
    
class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'blog/password_reset_done.html'

class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'blog/password_reset_confirm.html'
    success_url = reverse_lazy('password_reset_complete')

class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'blog/password_reset_complete.html'


# Authentication Views
# Registration disabled - admin only system
# def register_view(request):
#     if request.user.is_authenticated:
#         return redirect('dashboard')
#     
#     if request.method == 'POST':
#         form = UserCreationForm(request.POST)
#         if form.is_valid():
#             user = form.save()
#             user.is_staff = True
#             user.save()
#             login(request, user)
#             messages.success(request, 'Account created successfully!')
#             return redirect('dashboard')
#     else:
#         form = UserCreationForm()
#     
#     return render(request, 'blog/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('dashboard')
    else:
        form = AuthenticationForm()
    
    return render(request, 'blog/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, 'Logged out successfully.')
    return redirect('blog_list')


# Dashboard Views
@login_required
@user_passes_test(is_admin)
def dashboard(request):
    status_filter = request.GET.get('status', 'all')
    search_query = request.GET.get('search', '')
    
    posts = BlogPost.objects.all()
    
    if status_filter == 'published':
        posts = posts.filter(status='published')
    elif status_filter == 'draft':
        posts = posts.filter(status='draft')
    
    if search_query:
        posts = posts.filter(
            Q(title__icontains=search_query) |
            Q(content__icontains=search_query) |
            Q(tags__name__icontains=search_query) |
            Q(category__name__icontains=search_query)
        ).distinct()
    
    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'search_query': search_query,
    }
    return render(request, 'blog/dashboard.html', context)


@login_required
@user_passes_test(is_admin)
def create_post(request):
    if request.method == 'POST':
        form = BlogPostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            
            if 'publish' in request.POST:
                post.status = 'published'
                post.published_at = timezone.now()
            else:
                post.status = 'draft'
            
            post.save()
            form.save_m2m()  # Save tags
            
            messages.success(request, f'Post "{post.title}" created successfully!')
            return redirect('dashboard')
    else:
        form = BlogPostForm()
    
    return render(request, 'blog/post_form.html', {'form': form, 'action': 'Create'})


@login_required
@user_passes_test(is_admin)
def edit_post(request, slug):
    post = get_object_or_404(BlogPost, slug=slug)
    
    if request.method == 'POST':
        form = BlogPostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            post = form.save(commit=False)
            
            if 'publish' in request.POST and post.status == 'draft':
                post.status = 'published'
                post.published_at = timezone.now()
            elif 'draft' in request.POST:
                post.status = 'draft'
            
            post.save()
            form.save_m2m()
            
            messages.success(request, f'Post "{post.title}" updated successfully!')
            return redirect('dashboard')
    else:
        form = BlogPostForm(instance=post)
    
    return render(request, 'blog/post_form.html', {'form': form, 'action': 'Edit', 'post': post})


@login_required
@user_passes_test(is_admin)
def delete_post(request, slug):
    post = get_object_or_404(BlogPost, slug=slug)
    
    if request.method == 'POST':
        title = post.title
        post.delete()
        messages.success(request, f'Post "{title}" deleted successfully!')
        return redirect('dashboard')
    
    return render(request, 'blog/post_confirm_delete.html', {'post': post})


# Public Blog Views
def blog_list(request):
    search_query = request.GET.get('search', '')
    
    posts = BlogPost.objects.filter(status='published')
    
    if search_query:
        posts = posts.filter(
            Q(title__icontains=search_query) |
            Q(excerpt__icontains=search_query) |
            Q(content__icontains=search_query) |
            Q(tags__name__icontains=search_query) |
            Q(category__name__icontains=search_query)
        ).distinct()
    
    paginator = Paginator(posts, 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }
    return render(request, 'blog/blog_list.html', context)


def blog_detail(request, slug):
    post = get_object_or_404(BlogPost, slug=slug, status='published')
    related_posts = BlogPost.objects.filter(
        status='published',
        category=post.category
    ).exclude(id=post.id)[:3]
    
    context = {
        'post': post,
        'related_posts': related_posts,
    }
    return render(request, 'blog/blog_detail.html', context)


# Author Profile Views
@login_required
@user_passes_test(is_admin)
def edit_profile(request):
    profile, created = AuthorProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = AuthorProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('edit_profile')
    else:
        form = AuthorProfileForm(instance=profile)
    
    context = {
        'form': form,
        'profile': profile,
    }
    return render(request, 'blog/edit_profile.html', context)


def author_profile(request, username):
    """Public view of author profile"""
    user = get_object_or_404(User, username=username)
    profile, created = AuthorProfile.objects.get_or_create(user=user)
    
    # Get published posts by this author
    posts = BlogPost.objects.filter(author=user, status='published')
    
    # Pagination
    paginator = Paginator(posts, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'author': user,
        'profile': profile,
        'page_obj': page_obj,
        'post_count': posts.count(),
    }
    return render(request, 'blog/author_profile.html', context)
