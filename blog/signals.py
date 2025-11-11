from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.management import call_command
from .models import BlogPost, Category, Tag
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=BlogPost)
def update_sitemap_on_post_save(sender, instance, created, **kwargs):
    """
    Update sitemap when a blog post is created or updated
    """
    if instance.status == 'published':
        try:
            # You can add custom sitemap update logic here if needed
            logger.info(f'Blog post {"created" if created else "updated"}: {instance.title}')
            # The sitemap will be automatically regenerated on next request
            # due to Django's sitemap framework
        except Exception as e:
            logger.error(f'Error updating sitemap: {e}')


@receiver(post_delete, sender=BlogPost)
def update_sitemap_on_post_delete(sender, instance, **kwargs):
    """
    Update sitemap when a blog post is deleted
    """
    try:
        logger.info(f'Blog post deleted: {instance.title}')
        # The sitemap will be automatically regenerated on next request
    except Exception as e:
        logger.error(f'Error updating sitemap on delete: {e}')


@receiver(post_save, sender=Category)
def update_sitemap_on_category_save(sender, instance, created, **kwargs):
    """
    Update sitemap when a category is created or updated
    """
    try:
        logger.info(f'Category {"created" if created else "updated"}: {instance.name}')
    except Exception as e:
        logger.error(f'Error updating sitemap: {e}')


@receiver(post_delete, sender=Category)
def update_sitemap_on_category_delete(sender, instance, **kwargs):
    """
    Update sitemap when a category is deleted
    """
    try:
        logger.info(f'Category deleted: {instance.name}')
    except Exception as e:
        logger.error(f'Error updating sitemap on delete: {e}')


@receiver(post_save, sender=Tag)
def update_sitemap_on_tag_save(sender, instance, created, **kwargs):
    """
    Update sitemap when a tag is created or updated
    """
    try:
        logger.info(f'Tag {"created" if created else "updated"}: {instance.name}')
    except Exception as e:
        logger.error(f'Error updating sitemap: {e}')


@receiver(post_delete, sender=Tag)
def update_sitemap_on_tag_delete(sender, instance, **kwargs):
    """
    Update sitemap when a tag is deleted
    """
    try:
        logger.info(f'Tag deleted: {instance.name}')
    except Exception as e:
        logger.error(f'Error updating sitemap on delete: {e}')
