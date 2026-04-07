from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User


class UserProfile(models.Model):
    USER_TYPES = [
        ('doctor', 'Doctor'),
        ('teacher', 'Teacher'),
        ('business_professional', 'Business Professional'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    user_type = models.CharField(max_length=30, choices=USER_TYPES, default='business_professional')
    custom_names = models.TextField(blank=True, help_text='Comma-separated list of names for better voice recognition')
    
    def __str__(self):
        return f"{self.user.username} - {self.get_user_type_display()}"
    
    def get_custom_names_list(self):
        """Returns list of custom names"""
        if not self.custom_names:
            return []
        return [name.strip() for name in self.custom_names.split(',') if name.strip()]


class Task(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=100)
    due_date = models.DateTimeField()
    reminder = models.BooleanField(default=False)
    completed = models.BooleanField(default=False)

    def __str__(self):
        return self.title


class JournalEntry(models.Model):
    MODES = [
        ('personal', 'Personal'),
        ('professional', 'Professional')
    ]

    MOOD_CHOICES = [
        ('happy', 'Happy'),
        ('optimistic', 'Optimistic'),
        ('neutral', 'Neutral'),
        ('sad', 'Sad'),
        ('angry', 'Angry'),
        ('anxious', 'Anxious'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=100)
    content = models.TextField()

    mood = models.CharField(
        max_length=20,
        choices=MOOD_CHOICES,
        default='neutral'
    )

    mood_confidence = models.FloatField(default=0.0)
    mode = models.CharField(
        max_length=20,
        choices=MODES,
        default='personal'
    )

    is_voice_entry = models.BooleanField(default=False)
    voice_transcript = models.TextField(blank=True, null=True)

    sentiment_polarity = models.FloatField(default=0.0)
    detected_emotions = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.mood})"
# Create your models here.