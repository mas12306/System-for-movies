# Generated migration to add comment field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0005_remove_movie_cover_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='useraction',
            name='comment',
            field=models.TextField(blank=True, null=True, verbose_name='评论'),
        ),
    ]

