# Complete blog/views.py - Copy this entire file

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
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
    """Main blog list view with search and filtering"""
    search_query = request.GET.get('search', '')
    selected_categories = request.GET.getlist('category')
    sort = request.GET.get('sort', '-published_at')
    
    posts = BlogPost.objects.filter(status='published')
    
    # Search functionality
    if search_query:
        posts = posts.filter(
            Q(title__icontains=search_query) |
            Q(excerpt__icontains=search_query) |
            Q(content__icontains=search_query) |
            Q(tags__name__icontains=search_query) |
            Q(category__name__icontains=search_query)
        ).distinct()
    
    # Category filtering
    if selected_categories:
        posts = posts.filter(category__slug__in=selected_categories)
    
    # Sorting
    posts = posts.order_by(sort)
    
    # Pagination
    paginator = Paginator(posts, 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get data for sidebar
    categories = Category.objects.annotate(post_count=Count('posts', filter=Q(posts__status='published')))
    all_categories = categories
    recent_posts = BlogPost.objects.filter(status='published').order_by('-published_at')[:5]
    popular_tags = Tag.objects.annotate(post_count=Count('posts', filter=Q(posts__status='published'))).order_by('-post_count')[:10]
    
    # Blog stats
    total_posts = BlogPost.objects.filter(status='published').count()
    total_categories = categories.count()
    total_authors = User.objects.filter(blog_posts__status='published').distinct().count()
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'selected_categories': selected_categories,
        'categories': categories,
        'all_categories': all_categories,
        'recent_posts': recent_posts,
        'popular_tags': popular_tags,
        'total_posts': total_posts,
        'total_categories': total_categories,
        'total_authors': total_authors,
        'sort': sort,
    }
    return render(request, 'blog/blog_list.html', context)


def blog_detail(request, slug):
    """Individual blog post detail view"""
    post = get_object_or_404(BlogPost, slug=slug, status='published')
    
    # Get related posts from same category
    related_posts = BlogPost.objects.filter(
        status='published',
        category=post.category
    ).exclude(id=post.id).order_by('-published_at')[:3]
    
    # Get recent posts for sidebar
    recent_posts = BlogPost.objects.filter(status='published').order_by('-published_at')[:5]
    
    # Get categories for sidebar
    categories = Category.objects.annotate(post_count=Count('posts', filter=Q(posts__status='published')))
    
    context = {
        'post': post,
        'related_posts': related_posts,
        'recent_posts': recent_posts,
        'categories': categories,
    }
    return render(request, 'blog/blog_detail.html', context)


def category_posts(request, slug):
    """View posts filtered by category"""
    category = get_object_or_404(Category, slug=slug)
    search_query = request.GET.get('search', '')
    sort = request.GET.get('sort', '-published_at')
    
    posts = BlogPost.objects.filter(status='published', category=category)
    
    # Search functionality
    if search_query:
        posts = posts.filter(
            Q(title__icontains=search_query) |
            Q(excerpt__icontains=search_query) |
            Q(content__icontains=search_query) |
            Q(tags__name__icontains=search_query)
        )
    
    # Sorting
    posts = posts.order_by(sort)
    
    # Pagination
    paginator = Paginator(posts, 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get sidebar data
    categories = Category.objects.annotate(post_count=Count('posts', filter=Q(posts__status='published')))
    recent_posts = BlogPost.objects.filter(status='published').order_by('-published_at')[:5]
    popular_tags = Tag.objects.annotate(post_count=Count('posts', filter=Q(posts__status='published'))).order_by('-post_count')[:10]
    
    # Blog stats
    total_posts = BlogPost.objects.filter(status='published').count()
    total_categories = categories.count()
    total_authors = User.objects.filter(blog_posts__status='published').distinct().count()
    
    context = {
        'page_obj': page_obj,
        'category': category,
        'search_query': search_query,
        'categories': categories,
        'recent_posts': recent_posts,
        'popular_tags': popular_tags,
        'total_posts': total_posts,
        'total_categories': total_categories,
        'total_authors': total_authors,
        'sort': sort,
    }
    return render(request, 'blog/category_posts.html', context)


def tag_posts(request, slug):
    """View posts filtered by tag"""
    tag = get_object_or_404(Tag, slug=slug)
    search_query = request.GET.get('search', '')
    sort = request.GET.get('sort', '-published_at')
    
    posts = BlogPost.objects.filter(status='published', tags=tag)
    
    # Search functionality
    if search_query:
        posts = posts.filter(
            Q(title__icontains=search_query) |
            Q(excerpt__icontains=search_query) |
            Q(content__icontains=search_query)
        )
    
    # Sorting
    posts = posts.order_by(sort)
    
    # Pagination
    paginator = Paginator(posts, 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get sidebar data
    categories = Category.objects.annotate(post_count=Count('posts', filter=Q(posts__status='published')))
    recent_posts = BlogPost.objects.filter(status='published').order_by('-published_at')[:5]
    popular_tags = Tag.objects.annotate(post_count=Count('posts', filter=Q(posts__status='published'))).order_by('-post_count')[:10]
    
    # Blog stats
    total_posts = BlogPost.objects.filter(status='published').count()
    total_categories = categories.count()
    total_authors = User.objects.filter(blog_posts__status='published').distinct().count()
    
    context = {
        'page_obj': page_obj,
        'tag': tag,
        'search_query': search_query,
        'categories': categories,
        'recent_posts': recent_posts,
        'popular_tags': popular_tags,
        'total_posts': total_posts,
        'total_categories': total_categories,
        'total_authors': total_authors,
        'sort': sort,
    }
    return render(request, 'blog/tag_posts.html', context)


# Author Profile Views
@login_required
@user_passes_test(is_admin)
def edit_profile(request):
    """Edit user's author profile"""
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
    """Public view of author profile with their posts"""
    user = get_object_or_404(User, username=username)
    profile, created = AuthorProfile.objects.get_or_create(user=user)
    
    # Get published posts by this author
    posts = BlogPost.objects.filter(author=user, status='published').order_by('-published_at')
    
    # Pagination
    paginator = Paginator(posts, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get sidebar data
    categories = Category.objects.annotate(post_count=Count('posts', filter=Q(posts__status='published')))
    recent_posts = BlogPost.objects.filter(status='published').order_by('-published_at')[:5]
    popular_tags = Tag.objects.annotate(post_count=Count('posts', filter=Q(posts__status='published'))).order_by('-post_count')[:10]
    
    # Blog stats
    total_posts = BlogPost.objects.filter(status='published').count()
    total_categories = categories.count()
    total_authors = User.objects.filter(blog_posts__status='published').distinct().count()
    
    context = {
        'author': user,
        'profile': profile,
        'page_obj': page_obj,
        'post_count': posts.count(),
        'categories': categories,
        'recent_posts': recent_posts,
        'popular_tags': popular_tags,
        'total_posts': total_posts,
        'total_categories': total_categories,
        'total_authors': total_authors,
    }
    return render(request, 'blog/author_profile.html', context)


def newsletter_subscribe(request):
    """Handle newsletter subscription"""
    if request.method == 'POST':
        email = request.POST.get('email', '')
        if email:
            # Here you would typically save to a newsletter model
            # For now, we'll just add a message
            messages.success(request, f'Thanks for subscribing! Check {email} for confirmation.')
            return redirect('blog_list')
    
    return redirect('blog_list')
