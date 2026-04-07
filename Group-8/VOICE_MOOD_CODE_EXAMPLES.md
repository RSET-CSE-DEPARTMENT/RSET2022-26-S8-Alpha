# Voice-to-Text with Mood Detection - Code Examples

## Django Views Examples

### Display Voice Entries with Mood in Dashboard

```python
# In dashboard/views.py

def dashboard(request):
    # Get recent voice entries
    voice_entries = JournalEntry.objects.filter(
        is_voice_entry=True
    ).order_by('-created_at')[:10]
    
    # Get mood statistics
    mood_stats = JournalEntry.objects.filter(
        is_voice_entry=True
    ).values('mood').annotate(count=Count('id'))
    
    # Get average sentiment
    avg_sentiment = JournalEntry.objects.filter(
        is_voice_entry=True
    ).aggregate(
        avg_polarity=Avg('sentiment_polarity'),
        avg_confidence=Avg('mood_confidence')
    )
    
    return render(request, 'dashboard/dashboard.html', {
        'voice_entries': voice_entries,
        'mood_stats': mood_stats,
        'avg_sentiment': avg_sentiment,
        'entries': entries,
        'tasks': tasks,
    })
```

### Filter Entries by Mood

```python
# Get all happy voice entries from past week
from django.utils import timezone
from datetime import timedelta

happy_entries = JournalEntry.objects.filter(
    is_voice_entry=True,
    mood='happy',
    created_at__gte=timezone.now() - timedelta(days=7)
).order_by('-created_at')

# Get anxious entries
anxious_entries = JournalEntry.objects.filter(
    is_voice_entry=True,
    mood='anxious'
)

# Get high-confidence mood entries
confident_entries = JournalEntry.objects.filter(
    is_voice_entry=True,
    mood_confidence__gte=0.8
)

# Get positive sentiment entries
positive_entries = JournalEntry.objects.filter(
    is_voice_entry=True,
    sentiment_polarity__gte=0.3
)
```

### Mood Analytics View

```python
from django.db.models import Avg, Count, Q
from django.http import JsonResponse

def mood_analytics(request):
    """Returns mood statistics and trends"""
    
    # Mood distribution
    mood_distribution = JournalEntry.objects.filter(
        is_voice_entry=True
    ).values('mood').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Confidence by mood
    confidence_by_mood = JournalEntry.objects.filter(
        is_voice_entry=True
    ).values('mood').annotate(
        avg_confidence=Avg('mood_confidence')
    )
    
    # Weekly mood trend
    this_week = timezone.now() - timedelta(days=7)
    weekly_moods = JournalEntry.objects.filter(
        is_voice_entry=True,
        created_at__gte=this_week
    ).values('mood').annotate(count=Count('id'))
    
    # Most common emotions
    from collections import Counter
    all_emotions = JournalEntry.objects.filter(
        is_voice_entry=True
    ).values_list('detected_emotions', flat=True)
    
    emotion_counts = Counter()
    for emotions in all_emotions:
        emotion_counts.update(emotions)
    
    return JsonResponse({
        'mood_distribution': list(mood_distribution),
        'confidence_by_mood': list(confidence_by_mood),
        'weekly_trend': list(weekly_moods),
        'common_emotions': dict(emotion_counts.most_common(10))
    })
```

## Template Examples

### Display Mood in Entry List

```django
<!-- In journal.html -->

{% for entry in entries %}
  <div class="journal-entry {% if entry.is_voice_entry %}voice-entry{% endif %}">
    <div class="entry-header">
      <h3>{{ entry.title }}</h3>
      {% if entry.is_voice_entry %}
        <span class="badge voice-badge">🎤 Voice Entry</span>
      {% endif %}
    </div>
    
    {% if entry.is_voice_entry %}
      <div class="mood-panel">
        <span class="mood-emoji">
          {% if entry.mood == 'happy' %}😊
          {% elif entry.mood == 'optimistic' %}🙂
          {% elif entry.mood == 'neutral' %}😐
          {% elif entry.mood == 'sad' %}😢
          {% elif entry.mood == 'angry' %}😠
          {% elif entry.mood == 'anxious' %}😰
          {% else %}😐{% endif %}
        </span>
        <div class="mood-info">
          <p class="mood">
            <strong>Mood:</strong> {{ entry.mood|title }}
            <span class="confidence">({{ entry.mood_confidence|floatformat:0 }}% confident)</span>
          </p>
          {% if entry.detected_emotions %}
            <p class="emotions">
              <strong>Emotions:</strong>
              {% for emotion in entry.detected_emotions %}
                <span class="emotion-tag">{{ emotion }}</span>
              {% endfor %}
            </p>
          {% endif %}
        </div>
      </div>
    {% endif %}
    
    <p class="content">{{ entry.content|truncatewords:50 }}</p>
    <p class="date">{{ entry.created_at|date:"Y-m-d H:i" }}</p>
  </div>
{% endfor %}
```

### Mood Statistics Card

```django
<!-- Dashboard mood widget -->

<div class="mood-stats-card">
  <h3>Your Mood This Week</h3>
  
  <div class="mood-chart">
    {% for stat in mood_stats %}
      <div class="mood-bar">
        <div class="bar-label">
          {% if stat.mood == 'happy' %}😊
          {% elif stat.mood == 'optimistic' %}🙂
          {% elif stat.mood == 'neutral' %}😐
          {% elif stat.mood == 'sad' %}😢
          {% elif stat.mood == 'angry' %}😠
          {% endif %}
          {{ stat.mood|title }}
        </div>
        <div class="bar">
          <div class="bar-fill" style="width: {{ stat.count|add:0|mul:20 }}px;">
            {{ stat.count }}
          </div>
        </div>
      </div>
    {% endfor %}
  </div>
  
  <div class="sentiment-summary">
    <p>Average Sentiment: <strong>{{ avg_sentiment.avg_polarity|floatformat:2 }}</strong></p>
    <p>Detection Confidence: <strong>{{ avg_sentiment.avg_confidence|floatformat:0 }}%</strong></p>
  </div>
</div>
```

## Management Command Example

```python
# dashboard/management/commands/mood_report.py

from django.core.management.base import BaseCommand
from django.db.models import Avg, Count
from django.utils import timezone
from datetime import timedelta
from dashboard.models import JournalEntry

class Command(BaseCommand):
    help = 'Generate mood report from voice entries'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days to analyze'
        )

    def handle(self, *args, **options):
        days = options['days']
        since = timezone.now() - timedelta(days=days)
        
        entries = JournalEntry.objects.filter(
            is_voice_entry=True,
            created_at__gte=since
        )
        
        self.stdout.write(f"Mood Report (Last {days} days)")
        self.stdout.write("=" * 40)
        
        # Mood distribution
        moods = entries.values('mood').annotate(count=Count('id'))
        for mood in moods:
            self.stdout.write(
                f"  {mood['mood'].title()}: {mood['count']} entries"
            )
        
        # Statistics
        stats = entries.aggregate(
            total=Count('id'),
            avg_confidence=Avg('mood_confidence'),
            avg_polarity=Avg('sentiment_polarity')
        )
        
        self.stdout.write("\nStatistics:")
        self.stdout.write(f"  Total entries: {stats['total']}")
        self.stdout.write(f"  Avg confidence: {stats['avg_confidence']:.2%}")
        self.stdout.write(f"  Avg polarity: {stats['avg_polarity']:.2f}")
        
        # Common emotions
        from collections import Counter
        emotions = entries.values_list('detected_emotions', flat=True)
        emotion_counter = Counter()
        for e_list in emotions:
            emotion_counter.update(e_list)
        
        self.stdout.write("\nTop emotions:")
        for emotion, count in emotion_counter.most_common(5):
            self.stdout.write(f"  {emotion}: {count}")
```

## Serializer Example (DRF)

```python
# dashboard/serializers.py (if using Django REST Framework)

from rest_framework import serializers
from .models import JournalEntry

class MoodAnalysisSerializer(serializers.ModelSerializer):
    mood_emoji = serializers.SerializerMethodField()
    is_positive = serializers.SerializerMethodField()
    
    class Meta:
        model = JournalEntry
        fields = [
            'id', 'title', 'content', 'mood', 'mood_emoji',
            'mood_confidence', 'sentiment_polarity', 
            'detected_emotions', 'is_positive', 'created_at'
        ]
    
    def get_mood_emoji(self, obj):
        emoji_map = {
            'happy': '😊',
            'optimistic': '🙂',
            'neutral': '😐',
            'sad': '😢',
            'angry': '😠',
            'anxious': '😰',
        }
        return emoji_map.get(obj.mood, '😐')
    
    def get_is_positive(self, obj):
        return obj.sentiment_polarity > 0.1

class MoodStatsSerializer(serializers.Serializer):
    mood = serializers.CharField()
    count = serializers.IntegerField()
    percentage = serializers.FloatField()
    avg_confidence = serializers.FloatField()
```

## Test Examples

```python
# dashboard/tests.py

from django.test import TestCase
from django.test.client import Client
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import JournalEntry
import json

class VoiceMoodDetectionTests(TestCase):
    def setUp(self):
        self.client = Client()
    
    def test_transcribe_endpoint(self):
        """Test transcription endpoint returns mood data"""
        # Create dummy audio file (WAV header)
        audio_content = b'RIFF\x00\x00\x00\x00WAVEfmt '
        audio_file = SimpleUploadedFile(
            "test.wav",
            audio_content,
            content_type="audio/wav"
        )
        
        response = self.client.post(
            '/transcribe/',
            {'file': audio_file}
        )
        
        # Should return JSON with mood data
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('mood', data)
        self.assertIn('mood_confidence', data)
        self.assertIn('emoji', data)
    
    def test_save_voice_entry(self):
        """Test saving voice entry with mood"""
        payload = {
            'text': 'I am very happy today!',
            'title': 'Happy Day',
            'mood': 'happy',
            'mood_confidence': 0.95,
            'polarity': 0.85,
            'detected_emotions': ['excited', 'grateful']
        }
        
        response = self.client.post(
            '/save-voice-entry/',
            json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        # Check entry was saved
        entry = JournalEntry.objects.get(id=data['entry_id'])
        self.assertEqual(entry.mood, 'happy')
        self.assertTrue(entry.is_voice_entry)
        self.assertIn('excited', entry.detected_emotions)
    
    def test_mood_detection_accuracy(self):
        """Test mood detection algorithm"""
        from echoapp.nlp_module.mood_detector import analyze_text_emotions
        
        # Test positive sentiment
        result = analyze_text_emotions("I love this! It's amazing!")
        self.assertIn(result['primary_mood'], ['happy', 'optimistic'])
        self.assertGreater(result['polarity'], 0.3)
        
        # Test negative sentiment
        result = analyze_text_emotions("This is terrible and awful")
        self.assertIn(result['primary_mood'], ['sad', 'angry'])
        self.assertLess(result['polarity'], -0.3)
        
        # Test neutral sentiment
        result = analyze_text_emotions("The weather is cloudy today")
        self.assertEqual(result['primary_mood'], 'neutral')
```

## Admin Interface Customization

```python
# dashboard/admin.py

from django.contrib import admin
from .models import JournalEntry, Task

@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ('title', 'mood', 'mood_confidence', 'is_voice_entry', 'created_at')
    list_filter = ('mood', 'is_voice_entry', 'created_at')
    search_fields = ('title', 'content')
    readonly_fields = ('mood_confidence', 'sentiment_polarity', 'detected_emotions')
    
    fieldsets = (
        ('Basic', {
            'fields': ('title', 'content', 'mode')
        }),
        ('Mood Analysis', {
            'fields': ('mood', 'mood_confidence', 'sentiment_polarity', 'detected_emotions')
        }),
        ('Voice Entry', {
            'fields': ('is_voice_entry', 'voice_transcript'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def has_delete_permission(self, request):
        return request.user.is_superuser
```

## Async Processing (Celery)

```python
# For high-volume transcription, use Celery

# tasks.py
from celery import shared_task
from echoapp.nlp_module.mood_detector import analyze_text_emotions

@shared_task
def transcribe_and_analyze(entry_id):
    """Async transcription and mood analysis"""
    entry = JournalEntry.objects.get(id=entry_id)
    
    try:
        # Perform analysis
        analysis = analyze_text_emotions(entry.voice_transcript)
        
        # Update entry
        entry.mood = analysis['primary_mood']
        entry.mood_confidence = analysis['mood_confidence']
        entry.sentiment_polarity = analysis['polarity']
        entry.detected_emotions = analysis['detected_emotions']
        entry.save()
        
        return {'status': 'success', 'entry_id': entry_id}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}
```

These examples demonstrate various ways to integrate and use the voice-to-text mood detection feature throughout your Django application.
