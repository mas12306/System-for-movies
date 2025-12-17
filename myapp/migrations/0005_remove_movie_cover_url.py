# Generated migration to remove cover_url field

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0004_movie_cover_url'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='movie',
            name='cover_url',
        ),
    ]


