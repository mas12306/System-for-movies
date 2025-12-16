from django.core.management.base import BaseCommand

from myapp.models import Movie


class Command(BaseCommand):
    help = "Sync cover_url to poster if poster is empty."

    def handle(self, *args, **options):
        updated = 0
        for m in Movie.objects.all():
            if m.cover_url and not m.poster:
                m.poster = m.cover_url
                m.save(update_fields=["poster"])
                updated += 1
        self.stdout.write(self.style.SUCCESS(f"Synced cover_url to poster for {updated} movies."))

