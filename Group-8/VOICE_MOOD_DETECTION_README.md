# Voice-to-Text with Mood Detection Feature

## Overview
This feature enables users to record or upload audio files, automatically transcribe them using OpenAI's Whisper model, and detect their emotional tone/mood in real-time.

## Features

### 1. **Audio Recording & Transcription**
- Browser-based audio recording using Web Audio API
- Support for audio file uploads (MP3, WAV, OGG, M4A, etc.)
- AI-powered transcription using OpenAI Whisper model
- Real-time transcription status updates

### 2. **Mood Detection**
- Automatic emotional sentiment analysis of transcribed text
- **Mood Categories**: Happy, Optimistic, Neutral, Sad, Angry, Anxious
- **Confidence Score**: 0-100% indicating detection certainty
- **Polarity Score**: -1 to +1 range indicating sentiment intensity
- **Emoji Representation**: Visual emoji for quick mood identification

### 3. **Emotion Analysis**
- Additional emotion keyword detection beyond primary mood
- Detects: excitement, anxiety, tiredness, gratitude, frustration
- Displayed as tags below mood panel

### 4. **Journal Integration**
- Save voice entries directly to journal database
- Stores: transcribed text, detected mood, confidence, polarity, detected emotions
- Tracks entries as voice-specific with `is_voice_entry` flag
- Original transcript preserved for reference

## Technology Stack

### Backend (Django)
- **Transcription**: OpenAI Whisper (base model)
- **Mood Detection**: Dual approach
  - Primary: Transformer-based (DistilBERT fine-tuned on SST-2)
  - Fallback: TextBlob sentiment analysis
- **Database**: Django ORM with SQLite

### Frontend
- **Recording**: Web Audio API (MediaRecorder API)
- **UI**: Responsive HTML5/CSS3
- **State Management**: Vanilla JavaScript

## Installation

### 1. Install Required Packages

```bash
pip install openai-whisper transformers textblob spacy
python -m spacy download en_core_web_sm
```

### 2. Database Migration

```bash
python manage.py migrate dashboard
```

This creates new fields in the JournalEntry model:
- `mood_confidence`: Confidence score (0-1)
- `is_voice_entry`: Boolean flag for voice entries
- `voice_transcript`: Original transcribed text
- `sentiment_polarity`: Polarity score (-1 to 1)
- `detected_emotions`: JSON array of detected emotions

### 3. Static Files

No additional static files needed. All styling is inline in the HTML template.

## Usage

### For Users

1. **Navigate to Voice Page**
   - Access via `/voice/` URL or dashboard menu

2. **Record Audio**
   - Click "Start Recording" button
   - Speak clearly into microphone
   - Click "Stop" when finished

3. **Or Upload File**
   - Click file input to select audio file
   - Supported formats: MP3, WAV, OGG, M4A

4. **Transcribe & Detect Mood**
   - Click "Transcribe & Detect Mood" button
   - Wait for transcription (typically 10-30 seconds)
   - View results:
     - Transcribed text in textarea
     - Mood panel with emoji, confidence, polarity
     - Additional emotions if detected

5. **Save to Journal**
   - Edit transcribed text if needed
   - Add optional title
   - Click "Save to Journal"
   - Entry saved with mood metadata

### For Developers

#### View Detected Mood in Templates

```django
{% for entry in entries %}
  {% if entry.is_voice_entry %}
    <div class="voice-entry">
      <h3>{{ entry.title }}</h3>
      <p>Mood: <strong>{{ entry.mood }}</strong></p>
      <p>Confidence: {{ entry.mood_confidence|floatformat:2 }}%</p>
      <p>{{ entry.content }}</p>
    </div>
  {% endif %}
{% endfor %}
```

#### Query Voice Entries with Specific Mood

```python
from dashboard.models import JournalEntry

# Get all happy voice entries
happy_entries = JournalEntry.objects.filter(
    is_voice_entry=True,
    mood='happy'
).order_by('-created_at')

# Get entries with high confidence mood detection
confident_entries = JournalEntry.objects.filter(
    is_voice_entry=True,
    mood_confidence__gte=0.8
)

# Get entries by emotion
anxious_entries = JournalEntry.objects.filter(
    detected_emotions__contains=['anxious']
)
```

#### Mood Analysis Statistics

```python
from django.db.models import Avg, Count

# Mood distribution
mood_counts = JournalEntry.objects.filter(
    is_voice_entry=True
).values('mood').annotate(count=Count('id'))

# Average confidence by mood
mood_confidence = JournalEntry.objects.filter(
    is_voice_entry=True
).values('mood').annotate(avg_confidence=Avg('mood_confidence'))

# Overall sentiment trend
sentiment_average = JournalEntry.objects.filter(
    is_voice_entry=True
).aggregate(Avg('sentiment_polarity'))
```

## API Endpoints

### 1. `/transcribe/` (POST)

**Request:**
```
Content-Type: multipart/form-data
- file: audio file
```

**Response:**
```json
{
  "text": "Transcribed text",
  "mood": "happy",
  "mood_confidence": 0.85,
  "polarity": 0.72,
  "emoji": "😊",
  "description": "Very positive sentiment detected",
  "detected_emotions": ["excited", "grateful"]
}
```

**Error:**
```json
{
  "error": "Error message",
  "details": "Additional details"
}
```

### 2. `/save-voice-entry/` (POST)

**Request:**
```json
{
  "text": "Entry text",
  "title": "Entry Title",
  "mood": "happy",
  "mood_confidence": 0.85,
  "polarity": 0.72,
  "detected_emotions": ["excited"]
}
```

**Response:**
```json
{
  "success": true,
  "message": "Voice entry saved successfully",
  "entry_id": 42,
  "emoji": "😊"
}
```

**Error:**
```json
{
  "error": "Error message"
}
```

## Model Changes

### JournalEntry Model (Updated)

```python
class JournalEntry(models.Model):
    title = models.CharField(max_length=100)
    content = models.TextField()
    mood = models.CharField(
        max_length=20,
        choices=[
            ('happy', 'Happy'),
            ('optimistic', 'Optimistic'),
            ('neutral', 'Neutral'),
            ('sad', 'Sad'),
            ('angry', 'Angry'),
            ('anxious', 'Anxious'),
        ],
        default='neutral'
    )
    mood_confidence = models.FloatField(default=0.0)  # 0-1
    mode = models.CharField(max_length=20, choices=MODES, default='personal')
    is_voice_entry = models.BooleanField(default=False)
    voice_transcript = models.TextField(blank=True, null=True)
    sentiment_polarity = models.FloatField(default=0.0)  # -1 to 1
    detected_emotions = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
```

## Mood Detection Algorithm

### Primary Method: Transformer-Based (DistilBERT)
- **Model**: distilbert-base-uncased-finetuned-sst-2-english
- **Accuracy**: ~92% on SST-2 dataset
- **Input limit**: 512 tokens
- **Output**: Positive/Negative classification with confidence

### Fallback Method: TextBlob
- **Metric**: Polarity (sentiment) and Subjectivity
- **Polarity Range**: -1 (negative) to +1 (positive)
- **Used when**: Transformer unavailable or fails

### Polarity-to-Mood Mapping

| Polarity Range | Mood | Description |
|---|---|---|
| > 0.5 | Happy | Very positive sentiment |
| 0.1 to 0.5 | Optimistic | Positive sentiment |
| -0.1 to 0.1 | Neutral | Neutral sentiment |
| -0.5 to -0.1 | Sad | Negative sentiment |
| < -0.5 | Angry | Very negative sentiment |

## Performance Considerations

### Whisper Model Sizes
- **tiny**: ~39M parameters, fastest (recommended for testing)
- **base**: ~74M parameters, good balance (default)
- **small**: ~244M parameters, higher accuracy
- **medium**: ~769M parameters, very high accuracy
- **large**: ~1550M parameters, best accuracy

**Current Config:** base model
**Load Time:** ~5-10 seconds on first startup
**Transcription Time:** 10-30 seconds depending on audio length

### Memory Usage
- Whisper Base: ~2GB VRAM
- Transformer Model: ~500MB
- Total: ~2.5GB recommended

### Optimization Tips
```python
# In settings.py, use tiny model for resource-constrained environments
# Change in views.py:
MODEL = whisper.load_model("tiny")  # instead of "base"

# Or disable transformer for TextBlob-only processing
# In mood_detector.py, modify initialization
```

## Troubleshooting

### Issue: "Whisper model not installed on server"
**Solution:**
```bash
pip install openai-whisper
# May require ffmpeg for audio processing
# Windows: choco install ffmpeg
# macOS: brew install ffmpeg
# Linux: apt-get install ffmpeg
```

### Issue: Transformer model fails to load
**Solution:** Falls back to TextBlob automatically, or disable transformer:
```python
# In mood_detector.py
USE_TRANSFORMER = False
```

### Issue: Microphone access denied
**Solution:** 
- Check browser permissions (chrome://settings/content/microphone)
- Use HTTPS in production (required for getUserMedia)
- Test in different browser

### Issue: Slow transcription
**Solution:**
- Use smaller Whisper model (tiny/small)
- Check system resources
- Ensure ffmpeg is installed for codec support

## Future Enhancements

1. **Real-time Mood Streaming**
   - Detect mood as user speaks (partial transcripts)

2. **Mood Trends**
   - Track mood over time with graphs
   - Weekly/monthly mood summaries

3. **Voice Biometrics**
   - Detect stress from voice patterns
   - Energy level analysis

4. **Custom Mood Categories**
   - User-defined mood categories
   - Personal emotion taxonomy

5. **Multi-language Support**
   - Support for multiple languages in transcription
   - Language-specific mood detection

6. **Audio Quality Analysis**
   - Noise level detection
   - Clarity scoring
   - Processing recommendations

## Security Considerations

1. **Audio Files**
   - Temporary files automatically deleted
   - No persistent storage of raw audio

2. **CSRF Protection**
   - `/transcribe/` endpoint uses `@csrf_exempt` (ensure trusted)
   - Consider adding token-based auth in production

3. **File Upload Limits**
   - Recommended: 25MB max file size
   - Add validation in middleware for production

4. **Data Privacy**
   - All processing done server-side
   - Audio not sent to external APIs
   - Transcripts stored in user's database

## License
Part of EchoJournal project
