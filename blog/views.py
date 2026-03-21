# Complete blog/views.py - Replace your entire file with this

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
from django.core.mail import send_mass_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .models import BlogPost, Category, Tag, AuthorProfile, NewsletterSubscriber
from .forms import BlogPostForm, AuthorProfileForm
import json
import re
import uuid
from functools import wraps
from django.db import OperationalError, DatabaseError, ProgrammingError
import logging
 
logger = logging.getLogger(__name__)
 
 
def safe_blog_view(fallback_template='500.html'):
    """
    Wrap any blog view. If the DB fails for any reason,
    renders 500.html (which has the silent auto-retry spinner)
    instead of crashing with a raw Django error page.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            try:
                return view_func(request, *args, **kwargs)
            except (OperationalError, DatabaseError, ProgrammingError) as e:
                logger.error(f"DB error in {view_func.__name__}: {e}")
                return render(request, fallback_template, status=200)
            except Exception as e:
                logger.error(f"Unexpected error in {view_func.__name__}: {e}")
                return render(request, fallback_template, status=200)
        return wrapper
    return decorator
# Import password reset views
from django.contrib.auth.views import (
    PasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView
)
from django.urls import reverse_lazy


# ==================== HELPER FUNCTIONS ====================

def is_admin(user):
    """Check if user is admin or staff"""
    return user.is_staff or user.is_superuser


def send_confirmation_email(subscriber):
    """Send confirmation email to new subscriber"""
    confirm_url = f"https://21k.tools/blog/newsletter/confirm/{subscriber.confirmation_token}/"
    
    subject = 'Confirm Your Newsletter Subscription - 21K Tools'
    
    html_message = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        color: white; 
                        padding: 30px; 
                        text-align: center;
                        border-radius: 10px 10px 0 0;">
                <h2 style="margin: 0;">Welcome to 21K Tools Newsletter!</h2>
            </div>
            
            <div style="background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px;">
                <p>Thank you for subscribing to our newsletter.</p>
                <p>Please confirm your subscription by clicking the button below:</p>
                <p style="margin: 30px 0; text-align: center;">
                    <a href="{confirm_url}" 
                       style="background: linear-gradient(135deg, #2563eb, #1d4ed8); 
                              color: white; 
                              padding: 14px 35px; 
                              text-decoration: none; 
                              border-radius: 30px; 
                              display: inline-block;
                              font-weight: bold;">
                        Confirm Subscription
                    </a>
                </p>
                <p style="color: #666; font-size: 14px;">
                    If the button doesn't work, copy and paste this link into your browser:<br>
                    <a href="{confirm_url}" style="color: #2563eb; word-break: break-all;">{confirm_url}</a>
                </p>
            </div>
            
            <div style="margin-top: 20px; padding: 15px; background: #fff; border-radius: 10px;">
                <p style="color: #999; font-size: 12px; margin: 0; text-align: center;">
                    If you didn't subscribe to this newsletter, please ignore this email.
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    plain_message = strip_tags(html_message)
    
    email = EmailMultiAlternatives(
        subject=subject,
        body=plain_message,
        from_email='TwentyK Tools <contact@21k.tools>',
        to=[subscriber.email]
    )
    email.attach_alternative(html_message, "text/html")
    email.send()


def send_new_post_notification(post):
    """Send notification to all active subscribers about new blog post"""
    subscribers = NewsletterSubscriber.objects.filter(is_active=True, confirmed=True)
    
    if not subscribers.exists():
        print("No active subscribers to notify")
        return
    
    post_url = f"https://21k.tools{post.get_absolute_url()}"
    
    subject = f'New Blog Post: {post.title} - 21K Tools'
    
    sent_count = 0
    failed_count = 0
    
    for subscriber in subscribers:
        unsubscribe_url = f"https://21k.tools/blog/newsletter/unsubscribe/{subscriber.confirmation_token}/"
        
        html_message = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                            color: white; 
                            padding: 30px; 
                            border-radius: 10px 10px 0 0;
                            text-align: center;">
                    <h1 style="margin: 0; font-size: 24px;">21K Tools Blog</h1>
                    <p style="margin: 10px 0 0 0; opacity: 0.9;">New Article Published!</p>
                </div>
                
                <div style="background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px;">
                    <h2 style="color: #2563eb; margin-top: 0; font-size: 22px;">{post.title}</h2>
                    
                    <p style="color: #64748b; font-size: 16px; line-height: 1.8;">
                        {post.excerpt}
                    </p>
                    
                    <p style="margin: 30px 0; text-align: center;">
                        <a href="{post_url}" 
                           style="background: linear-gradient(135deg, #2563eb, #1d4ed8); 
                                  color: white; 
                                  padding: 14px 35px; 
                                  text-decoration: none; 
                                  border-radius: 30px; 
                                  display: inline-block; 
                                  font-weight: bold;">
                            Read Full Article →
                        </a>
                    </p>
                    
                    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e2e8f0;">
                        <p style="color: #64748b; font-size: 14px; margin: 0;">
                            <strong>Category:</strong> {post.category.name if post.category else 'General'}
                        </p>
                        <p style="color: #64748b; font-size: 14px; margin: 5px 0 0 0;">
                            <strong>Author:</strong> {post.author.get_full_name() or post.author.username}
                        </p>
                        <p style="color: #64748b; font-size: 14px; margin: 5px 0 0 0;">
                            <strong>Published:</strong> {post.published_at.strftime('%B %d, %Y')}
                        </p>
                    </div>
                </div>
                
                <div style="margin-top: 20px; padding: 20px; background: #fff; border-radius: 10px; text-align: center;">
                    <p style="color: #999; font-size: 12px; margin: 0;">
                        You're receiving this email because you subscribed to 21K Tools newsletter.
                    </p>
                    <p style="margin: 10px 0 0 0;">
                        <a href="{unsubscribe_url}" style="color: #2563eb; text-decoration: none; font-size: 12px;">
                            Unsubscribe from newsletter
                        </a>
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        plain_message = strip_tags(html_message)
        
        try:
            email = EmailMultiAlternatives(
                subject=subject,
                body=plain_message,
                from_email='TwentyK Tools <contact@21k.tools>',
                to=[subscriber.email]
            )
            email.attach_alternative(html_message, "text/html")
            email.send()
            sent_count += 1
        except Exception as e:
            failed_count += 1
            print(f"Failed to send email to {subscriber.email}: {e}")
    
    print(f"Newsletter sent: {sent_count} successful, {failed_count} failed")
    return sent_count, failed_count


# ==================== PASSWORD RESET VIEWS ====================

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


# ==================== AUTHENTICATION VIEWS ====================

def login_view(request):
    """User login view"""
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
                messages.success(request, f'Welcome back, {username}!')
                return redirect('dashboard')
    else:
        form = AuthenticationForm()
    
    return render(request, 'blog/login.html', {'form': form})


def logout_view(request):
    """User logout view"""
    logout(request)
    messages.info(request, 'Logged out successfully.')
    return redirect('blog_list')


# ==================== DASHBOARD VIEWS ====================

@login_required
@user_passes_test(is_admin)
def dashboard(request):
    """Admin dashboard view"""
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
    """Create new blog post"""
    if request.method == 'POST':
        form = BlogPostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            
            if 'publish' in request.POST:
                post.status = 'published'
                post.published_at = timezone.now()
                post.save()
                form.save_m2m()
                
                # Send newsletter to subscribers
                try:
                    sent, failed = send_new_post_notification(post)
                    messages.success(
                        request, 
                        f'Post "{post.title}" published! Newsletter sent to {sent} subscribers.'
                    )
                except Exception as e:
                    messages.warning(
                        request, 
                        f'Post published but failed to send newsletter: {str(e)}'
                    )
            else:
                post.status = 'draft'
                post.save()
                form.save_m2m()
                messages.success(request, f'Post "{post.title}" saved as draft!')
            
            return redirect('dashboard')
    else:
        form = BlogPostForm()
    
    return render(request, 'blog/post_form.html', {'form': form, 'action': 'Create'})


@login_required
@user_passes_test(is_admin)
def edit_post(request, slug):
    """Edit existing blog post"""
    post = get_object_or_404(BlogPost, slug=slug)
    was_draft = post.status == 'draft'
    
    if request.method == 'POST':
        form = BlogPostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            post = form.save(commit=False)
            
            if 'publish' in request.POST and was_draft:
                post.status = 'published'
                post.published_at = timezone.now()
                post.save()
                form.save_m2m()
                
                # Send newsletter when publishing for first time
                try:
                    sent, failed = send_new_post_notification(post)
                    messages.success(
                        request, 
                        f'Post "{post.title}" published! Newsletter sent to {sent} subscribers.'
                    )
                except Exception as e:
                    messages.warning(
                        request, 
                        f'Post published but failed to send newsletter: {str(e)}'
                    )
            elif 'draft' in request.POST:
                post.status = 'draft'
                post.save()
                form.save_m2m()
                messages.success(request, f'Post "{post.title}" saved as draft!')
            else:
                post.save()
                form.save_m2m()
                messages.success(request, f'Post "{post.title}" updated!')
            
            return redirect('dashboard')
    else:
        form = BlogPostForm(instance=post)
    
    return render(request, 'blog/post_form.html', {'form': form, 'action': 'Edit', 'post': post})


@login_required
@user_passes_test(is_admin)
def delete_post(request, slug):
    """Delete blog post"""
    post = get_object_or_404(BlogPost, slug=slug)
    
    if request.method == 'POST':
        title = post.title
        post.delete()
        messages.success(request, f'Post "{title}" deleted successfully!')
        return redirect('dashboard')
    
    return render(request, 'blog/post_confirm_delete.html', {'post': post})


# ==================== PUBLIC BLOG VIEWS ====================
@safe_blog_view()
def blog_list(request):
    """Main blog list view with search and filtering"""
    search_query = request.GET.get('search', '')
    selected_categories = request.GET.getlist('category')
    sort = request.GET.get('sort', '-published_at')
    
    posts = BlogPost.objects.filter(status='published').select_related('author', 'category').prefetch_related('tags')
    
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
    
    # Get data for sidebar - FIXED: Ensure we're getting categories with posts
    categories = Category.objects.annotate(
        post_count=Count('posts', filter=Q(posts__status='published'))
    ).filter(post_count__gt=0).order_by('name')
    
    recent_posts = BlogPost.objects.filter(status='published').select_related('author', 'category').order_by('-published_at')[:5]
    
    popular_tags = Tag.objects.annotate(
        post_count=Count('posts', filter=Q(posts__status='published'))
    ).filter(post_count__gt=0).order_by('-post_count')[:10]
    
    # Blog stats
    total_posts = BlogPost.objects.filter(status='published').count()
    total_categories = categories.count()
    total_authors = User.objects.filter(blog_posts__status='published').distinct().count()
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'selected_categories': selected_categories,
        'categories': categories,
        'all_categories': categories,  # Same as categories for consistency
        'recent_posts': recent_posts,
        'popular_tags': popular_tags,
        'total_posts': total_posts,
        'total_categories': total_categories,
        'total_authors': total_authors,
        'sort': sort,
    }
    return render(request, 'blog/blog_list.html', context)

# Add this to your blog_detail view in views.py to debug tags
@safe_blog_view()
def blog_detail(request, slug):
    """Individual blog post detail view"""
    post = get_object_or_404(
        BlogPost.objects.select_related('author', 'category').prefetch_related('tags'), 
        slug=slug, 
        status='published'
    )
    
    # DEBUG: Print tags to console
    print(f"Post: {post.title}")
    print(f"Tags count: {post.tags.count()}")
    print(f"Tags: {[tag.name for tag in post.tags.all()]}")
    
    # Calculate reading time (average reading speed: 200 words per minute)
    text = re.sub('<[^<]+?>', '', post.content)
    word_count = len(text.split())
    reading_time = max(1, round(word_count / 200))  # Minimum 1 minute
    
    # Get related posts from same category
    related_posts = BlogPost.objects.filter(
        status='published',
        category=post.category
    ).exclude(id=post.id).select_related('author', 'category').prefetch_related('tags').order_by('-published_at')[:3]
    
    # Get recent posts for sidebar
    recent_posts = BlogPost.objects.filter(status='published').select_related('author', 'category').order_by('-published_at')[:5]
    
    # Get categories for sidebar
    categories = Category.objects.annotate(
        post_count=Count('posts', filter=Q(posts__status='published'))
    ).filter(post_count__gt=0)
    
    # Handle comment form
    from django import forms
    
    class DummyCommentForm(forms.Form):
        name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your name'}))
        email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'your@email.com'}))
        content = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Share your thoughts...'}))
    
    if request.method == 'POST':
        form = DummyCommentForm(request.POST)
        if form.is_valid():
            messages.success(request, 'Thank you for your comment! It will be reviewed shortly.')
            return redirect('blog_detail', slug=slug)
    else:
        form = DummyCommentForm()
    
    # Dummy comments
    comments = []
    comment_count = 0
    
    context = {
        'post': post,
        'related_posts': related_posts,
        'recent_posts': recent_posts,
        'categories': categories,
        'reading_time': reading_time,
        'comments': comments,
        'comment_count': comment_count,
        'form': form,
    }
    return render(request, 'blog/blog_detail.html', context)

@safe_blog_view()
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

@safe_blog_view()
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


# ==================== AUTHOR PROFILE VIEWS ====================

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

@safe_blog_view()
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


# ==================== NEWSLETTER VIEWS ====================

def newsletter_subscribe(request):
    """Handle newsletter subscription"""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        
        if email:
            # Check if already subscribed
            subscriber, created = NewsletterSubscriber.objects.get_or_create(
                email=email,
                defaults={'confirmation_token': str(uuid.uuid4())}
            )
            
            if created:
                # Send confirmation email
                try:
                    send_confirmation_email(subscriber)
                    messages.success(
                        request, 
                        f'Thanks for subscribing! Please check {email} to confirm your subscription.'
                    )
                except Exception as e:
                    messages.error(request, 'Failed to send confirmation email. Please try again.')
                    print(f"Email error: {e}")
            else:
                if subscriber.confirmed:
                    messages.info(request, 'This email is already subscribed!')
                else:
                    # Resend confirmation
                    try:
                        send_confirmation_email(subscriber)
                        messages.info(request, 'Confirmation email resent. Please check your inbox.')
                    except Exception as e:
                        messages.error(request, 'Failed to send confirmation email.')
                        print(f"Email error: {e}")
        else:
            messages.error(request, 'Please enter a valid email address.')
    
    return redirect(request.META.get('HTTP_REFERER', 'blog_list'))


def confirm_subscription(request, token):
    """Confirm newsletter subscription"""
    try:
        subscriber = NewsletterSubscriber.objects.get(confirmation_token=token)
        subscriber.confirmed = True
        subscriber.is_active = True
        subscriber.save()
        
        messages.success(request, '✅ Your subscription is confirmed! You will receive new blog updates.')
        return redirect('blog_list')
    except NewsletterSubscriber.DoesNotExist:
        messages.error(request, 'Invalid confirmation link.')
        return redirect('blog_list')


def unsubscribe_newsletter(request, token):
    """Unsubscribe from newsletter"""
    try:
        subscriber = NewsletterSubscriber.objects.get(confirmation_token=token)
        subscriber.is_active = False
        subscriber.save()
        
        messages.success(request, 'You have been unsubscribed from our newsletter.')
        return redirect('blog_list')
    except NewsletterSubscriber.DoesNotExist:
        messages.error(request, 'Invalid unsubscribe link.')
        return redirect('blog_list')
# Add these new views to your blog/views.py file

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from .models import BlogPost, AuthorProfile
@safe_blog_view()
def serve_blog_thumbnail(request, slug):
    """Serve blog post thumbnail from database"""
    post = get_object_or_404(BlogPost, slug=slug)
    
    if not post.thumbnail_data:
        # Return a 404 or default image
        return HttpResponse(status=404)
    
    response = HttpResponse(post.thumbnail_data, content_type=post.thumbnail_type or 'image/jpeg')
    response['Content-Disposition'] = f'inline; filename="{post.thumbnail_name}"'
    return response

@safe_blog_view()
def serve_author_profile_picture(request, username):
    """Serve author profile picture from database"""
    from django.contrib.auth.models import User
    
    user = get_object_or_404(User, username=username)
    profile = get_object_or_404(AuthorProfile, user=user)
    
    if not profile.profile_picture_data:
        # Return a 404 or default image
        return HttpResponse(status=404)
    
    response = HttpResponse(profile.profile_picture_data, content_type=profile.profile_picture_type or 'image/jpeg')
    response['Content-Disposition'] = f'inline; filename="{profile.profile_picture_name}"'
    return response
