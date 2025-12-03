from django.core.management.base import BaseCommand
import migrations

class Command(BaseCommand):
    help = 'Initialize the database with tables and default users'

    def handle(self, *args, **options):
        self.stdout.write('Initializing database...')
        try:
            migrations.init_db()
            self.stdout.write(self.style.SUCCESS('Database initialized successfully'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error initializing database: {e}'))
