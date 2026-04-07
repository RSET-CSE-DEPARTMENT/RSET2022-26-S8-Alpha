# Generated migration for voice entry mood detection

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='journalentry',
            name='mood',
            field=models.CharField(
                choices=[
                    ('happy', 'Happy'),
                    ('optimistic', 'Optimistic'),
                    ('neutral', 'Neutral'),
                    ('sad', 'Sad'),
                    ('angry', 'Angry'),
                    ('anxious', 'Anxious'),
                ],
                default='neutral',
                max_length=20
            ),
        ),
        migrations.AddField(
            model_name='journalentry',
            name='mood_confidence',
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name='journalentry',
            name='is_voice_entry',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='journalentry',
            name='voice_transcript',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='journalentry',
            name='sentiment_polarity',
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name='journalentry',
            name='detected_emotions',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AlterModelOptions(
            name='journalentry',
            options={'ordering': ['-created_at']},
        ),
    ]
