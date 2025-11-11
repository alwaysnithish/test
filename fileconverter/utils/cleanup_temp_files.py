
import os
import time
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Clean up temporary conversion files older than 60 minutes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--age',
            type=int,
            default=60,
            help='Delete files older than this many minutes (default: 60)'
        )

    def handle(self, *args, **options):
        age_minutes = options['age']
        temp_dir = getattr(settings, 'MEDIA_TEMP', os.path.join(settings.MEDIA_ROOT, 'temp_conversions'))
        
        if not os.path.exists(temp_dir):
            self.stdout.write(self.style.WARNING(f'Temp directory does not exist: {temp_dir}'))
            return

        current_time = time.time()
        age_seconds = age_minutes * 60
        deleted_count = 0
        total_size = 0

        self.stdout.write(f'Scanning {temp_dir} for files older than {age_minutes} minutes...')

        for file_path in Path(temp_dir).glob('*'):
            if file_path.is_file():
                file_age = current_time - file_path.stat().st_mtime
                
                if file_age > age_seconds:
                    file_size = file_path.stat().st_size
                    try:
                        file_path.unlink()
                        deleted_count += 1
                        total_size += file_size
                        self.stdout.write(f'Deleted: {file_path.name} ({self._format_size(file_size)})')
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'Error deleting {file_path.name}: {str(e)}'))

        self.stdout.write(
            self.style.SUCCESS(
                f'\nCleanup complete: {deleted_count} files deleted, {self._format_size(total_size)} freed'
            )
        )

    def _format_size(self, bytes):
        """Format bytes to human readable size"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes < 1024.0:
                return f'{bytes:.2f} {unit}'
            bytes /= 1024.0
        return f'{bytes:.2f} TB'
