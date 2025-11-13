# Generated manually on 2025-11-02

from django.db import migrations


def configure_site_domain(apps, schema_editor):
    """
    Configure the Django Site to use 21k.tools domain.
    This replaces the default 'example.com' with your actual domain.
    """
    try:
        Site = apps.get_model('sites', 'Site')
        
        # Get or create site with ID 1
        site, created = Site.objects.get_or_create(
            pk=1,
            defaults={
                'domain': '21k.tools',
                'name': '21K Tools'
            }
        )
        
        # Update if it already exists with wrong domain
        if not created and site.domain != '21k.tools':
            site.domain = '21k.tools'
            site.name = '21K Tools'
            site.save()
            
    except Exception as e:
        # If sites framework isn't installed yet, skip silently
        pass


def revert_site_domain(apps, schema_editor):
    """
    Revert to example.com (for rollback purposes).
    """
    try:
        Site = apps.get_model('sites', 'Site')
        site = Site.objects.get(pk=1)
        site.domain = 'example.com'
        site.name = 'example.com'
        site.save()
    except Exception:
        pass


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0004_remove_authorprofile_profile_picture_and_more'),
        ('sites', '0002_alter_domain_unique'),
    ]

    operations = [
        migrations.RunPython(
            configure_site_domain,
            reverse_code=revert_site_domain,
        ),
    ]
