from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import BlogPost, Category, Tag

class BlogPostSitemap(Sitemap):
    """Sitemap for blog posts"""
    changefreq = "weekly"
    priority = 0.9

    def items(self):
        return BlogPost.objects.filter(status='published').order_by('-published_at')

    def lastmod(self, item):
        return item.updated_at

    def location(self, item):
        return reverse('blog_detail', args=[item.slug])


class BlogCategorySitemap(Sitemap):
    """Sitemap for blog categories"""
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return Category.objects.all()

    def lastmod(self, item):
        # Get the last updated post in this category
        last_post = BlogPost.objects.filter(
            category=item, 
            status='published'
        ).order_by('-updated_at').first()
        return last_post.updated_at if last_post else item.created_at

    def location(self, item):
        return reverse('category_posts', args=[item.slug])


class BlogTagSitemap(Sitemap):
    """Sitemap for blog tags"""
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        return Tag.objects.all()

    def lastmod(self, item):
        # Get the last updated post with this tag
        last_post = BlogPost.objects.filter(
            tags=item, 
            status='published'
        ).order_by('-updated_at').first()
        return last_post.updated_at if last_post else item.created_at

    def location(self, item):
        return reverse('tag_posts', args=[item.slug])


class BlogStaticSitemap(Sitemap):
    """Sitemap for static blog pages"""
    changefreq = "monthly"
    priority = 0.8

    def items(self):
        return ['blog_list']

    def location(self, item):
        return reverse(item)
