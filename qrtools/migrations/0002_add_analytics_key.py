from django.db import migrations, models
import secrets
import string


def generate_analytics_keys(apps, schema_editor):
    """Generate unique analytics_key for existing QRCode records"""
    QRCode = apps.get_model('qrtools', 'QRCode')
    
    def generate_short_code(length=10):
        chars = string.ascii_uppercase + string.digits
        return ''.join(secrets.choice(chars) for _ in range(length))
    
    for qr_code in QRCode.objects.all():
        while True:
            key = generate_short_code(length=10)
            if not QRCode.objects.filter(analytics_key=key).exists():
                qr_code.analytics_key = key
                qr_code.save(update_fields=['analytics_key'])
                break


class Migration(migrations.Migration):

    dependencies = [
        ('qrtools', '0001_initial'),  # Update to your latest migration
    ]

    operations = [
        # Step 1: Add analytics_key field as nullable
        migrations.AddField(
            model_name='qrcode',
            name='analytics_key',
            field=models.CharField(max_length=10, null=True, blank=True, db_index=True),
        ),
        
        # Step 2: Add logo padding fields
        migrations.AddField(
            model_name='qrcode',
            name='logo_padding',
            field=models.IntegerField(default=30, help_text='Padding around logo percentage'),
        ),
        migrations.AddField(
            model_name='qrcode',
            name='logo_border',
            field=models.BooleanField(default=True, help_text='Add border around logo'),
        ),
        
        # Step 3: Add 'rounded' to logo_shape choices
        migrations.AlterField(
            model_name='qrcode',
            name='logo_shape',
            field=models.CharField(max_length=10, choices=[
                ('square', 'Square'),
                ('circle', 'Circle'),
                ('rounded', 'Rounded'),
            ], default='square'),
        ),
        
        # Step 4: Generate unique keys for existing records
        migrations.RunPython(
            generate_analytics_keys,
            reverse_code=migrations.RunPython.noop
        ),
        
        # Step 5: Make analytics_key required and unique
        migrations.AlterField(
            model_name='qrcode',
            name='analytics_key',
            field=models.CharField(max_length=10, unique=True, db_index=True),
        ),
    ]
