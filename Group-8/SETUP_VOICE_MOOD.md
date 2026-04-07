# Voice-to-Text with Mood Detection - Quick Setup Guide

## Prerequisites
- Python 3.8+
- Django 5.2+
- FFmpeg (for audio processing)

## Installation Steps

### 1. Install Required Packages

```bash
pip install openai-whisper transformers torch textblob spacy
python -m spacy download en_core_web_sm
```

### 2. Update Database

```bash
python manage.py makemigrations dashboard
python manage.py migrate
```

### 3. Test the Feature

```bash
python manage.py runserver
# Visit: http://localhost:8000/voice/
```

## What Was Added

### New Files
- `echoapp/nlp_module/mood_detector.py` - Mood detection logic
- `dashboard/migrations/0002_voice_mood_detection.py` - Database migration
- `VOICE_MOOD_DETECTION_README.md` - Complete documentation

### Modified Files

#### `dashboard/models.py`
- Added `mood_confidence`, `is_voice_entry`, `voice_transcript`, `sentiment_polarity`, `detected_emotions` fields to JournalEntry
- Enhanced mood choices with 6 categories

#### `dashboard/views.py`
- Imported mood detection module
- Enhanced `/transcribe/` endpoint to return mood data
- Added `/save-voice-entry/` endpoint for saving entries with mood

#### `dashboard/urls.py`
- Added URL route for `/save-voice-entry/`

#### `dashboard/templates/dashboard/voice.html`
- Complete UI redesign with mood detection panel
- Added real-time mood display with emoji
- Added confidence bar and polarity score
- Added emotion tags display
- Enhanced UX with status indicators and alerts

## Feature Overview

### Voice Recording & Transcription
- 🎤 Record audio directly from browser
- 📂 Upload audio files (MP3, WAV, OGG, M4A)
- ✨ AI-powered transcription using OpenAI Whisper
- ⚡ Real-time status updates

### Mood Detection
- 😊 Automatic mood detection (Happy, Optimistic, Neutral, Sad, Angry, Anxious)
- 📊 Confidence scoring (0-100%)
- 📈 Polarity analysis (-1 to +1)
- 🏷️ Additional emotion detection (excited, anxious, tired, grateful, frustrated)

### Journal Integration
- 💾 Save voice entries with detected mood
- 🔍 Track mood trends over time
- 📝 Edit and customize entries
- 🎯 Filter by mood or emotion

## Quick Test

1. Go to http://localhost:8000/voice/
2. Click "Start Recording" and speak a sentence
3. Click "Stop" when done
4. Click "Transcribe & Detect Mood"
5. Wait for transcription and mood analysis
6. Review the mood panel showing:
   - Emoji representation
   - Mood category
   - Confidence percentage
   - Polarity score
   - Detected emotions
7. Click "Save to Journal" to store the entry

## Database Fields Added to JournalEntry

```python
mood_confidence = FloatField()  # 0-1 confidence
is_voice_entry = BooleanField()  # True for voice entries
voice_transcript = TextField()  # Original transcribed text
sentiment_polarity = FloatField()  # -1 to 1 sentiment
detected_emotions = JSONField()  # Array of detected emotions
```

## API Endpoints

### POST /transcribe/
Transcribes audio and detects mood

**Request:** multipart/form-data with audio file
**Response:** JSON with text, mood, confidence, polarity, emotions

### POST /save-voice-entry/
Saves voice entry to journal with mood data

**Request:** JSON with text, mood, confidence, polarity, emotions
**Response:** JSON with success status and entry ID

## Customization

### Change Mood Categories
Edit `dashboard/models.py` - JournalEntry.MOOD_CHOICES

### Use Different Whisper Model
Edit `dashboard/views.py`:
```python
MODEL = whisper.load_model("tiny")  # or small, medium, large
```

### Disable Transformer Model
Edit `echoapp/nlp_module/mood_detector.py`:
```python
USE_TRANSFORMER = False  # Falls back to TextBlob
```

## Troubleshooting

### Microphone not working?
- Check browser permissions
- Use HTTPS in production
- Test in different browser

### Transcription slow?
- Use smaller Whisper model (tiny)
- Check system resources
- Ensure FFmpeg installed

### Mood detection failing?
- Check transformers library installed
- Falls back to TextBlob automatically
- Check logs for detailed errors

## Performance Tips

- **First startup:** Model loads automatically (~10 seconds)
- **Typical transcription:** 10-30 seconds for 1 minute audio
- **Memory usage:** ~2.5GB recommended
- **Best results:** Clear speech, minimal background noise

## Production Considerations

1. Add file size limits (recommended 25MB max)
2. Add rate limiting on transcribe endpoint
3. Consider using smaller model for high volume
4. Set up proper logging and monitoring
5. Use HTTPS for getUserMedia API
6. Consider adding authentication to endpoints
7. Monitor memory usage on shared hosting

## Next Steps

- View saved entries in journal with mood stats
- Create mood trend reports
- Filter entries by detected emotions
- Build mood charts and analytics
- Add mood-based recommendations

For more details, see: `VOICE_MOOD_DETECTION_README.md`
