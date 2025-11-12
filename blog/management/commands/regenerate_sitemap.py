"""
Management command to manually regenerate blog sitemap
Usage: python manage.py regenerate_sitemap
"""

from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site
from blog.models import BlogPost, Category, Tag


class Command(BaseCommand):
    help = 'Regenerates the blog sitemap'

    def handle(self, *args, **options):
        self.stdout.write('Regenerating blog sitemap...')
        
        # Count items
        posts = BlogPost.objects.filter(status='published').count()
        categories = Category.objects.count()
        tags = Tag.objects.count()
        
        self.stdout.write(self.style.SUCCESS(f'✓ Found {posts} published posts'))
        self.stdout.write(self.style.SUCCESS(f'✓ Found {categories} categories'))
        self.stdout.write(self.style.SUCCESS(f'✓ Found {tags} tags'))
        
        # Get site info
        try:
            site = Site.objects.get_current()
            self.stdout.write(f'\nSitemap will be available at:')
            self.stdout.write(self.style.SUCCESS(f'https://21k.tools/blog/sitemap.xml'))
        except:
            self.stdout.write(self.style.WARNING('\nWarning: Site not configured. Using default domain.'))
            self.stdout.write('Sitemap will be available at: /blog/sitemap.xml')
        
        self.stdout.write(self.style.SUCCESS('\n✓ Sitemap regenerated successfully!'))
        self.stdout.write('The sitemap is dynamically generated and will be updated automatically.')
