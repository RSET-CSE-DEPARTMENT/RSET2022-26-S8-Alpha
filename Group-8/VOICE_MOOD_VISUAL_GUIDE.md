# Voice-to-Text with Mood Detection - Visual Guide

## 🎯 Feature Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                    USER STARTS AT /voice/                   │
└─────────────────────────────────────────────────────────────┘
                            ↓
                    ┌───────────────┐
                    │  Three Options │
                    └───────────────┘
                    ↙       ↓       ↖
            ┌──────────┐  ┌──────────┐  ┌──────────┐
            │ Record   │  │ Upload   │  │ Microphone
            │ Audio    │  │ File     │  │ Required
            └──────────┘  └──────────┘  └──────────┘
                    ↓       ↓       ↓
                    └───────────────┘
                            ↓
            ┌──────────────────────────────┐
            │  Click "Transcribe & Detect  │
            │          Mood"               │
            └──────────────────────────────┘
                            ↓
            ┌──────────────────────────────┐
            │   BACKEND PROCESSING         │
            │  ┌──────────────────────────┐│
            │  │ 1. Whisper Transcription ││
            │  │ 2. Mood Detection (Dual) ││
            │  │ 3. Emotion Analysis      ││
            │  └──────────────────────────┘│
            └──────────────────────────────┘
                            ↓
            ┌──────────────────────────────┐
            │   FRONTEND DISPLAY           │
            │  ┌──────────────────────────┐│
            │  │ • Transcribed Text      ││
            │  │ • Mood Emoji (😊)       ││
            │  │ • Confidence: 85%       ││
            │  │ • Polarity: 0.72        ││
            │  │ • Emotions: excited...  ││
            │  └──────────────────────────┘│
            └──────────────────────────────┘
                            ↓
            ┌──────────────────────────────┐
            │  Add Title (Optional)        │
            │  Edit Text (Optional)        │
            │  Click "Save to Journal"     │
            └──────────────────────────────┘
                            ↓
            ┌──────────────────────────────┐
            │  Save to Database with Mood  │
            │  ✓ Entry Created             │
            │  ✓ Mood Stored               │
            │  ✓ Success Message           │
            └──────────────────────────────┘
```

## 🏗️ Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      FRONTEND (Browser)                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  voice.html - HTML5 + CSS3 + Vanilla JavaScript      │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │ • Recording Controls (Start/Stop/Play)               │  │
│  │ • File Upload Input                                  │  │
│  │ • Transcription Textarea                             │  │
│  │ • Mood Detection Panel (Dynamic)                     │  │
│  │ • Alert System                                       │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↓ HTTP
┌─────────────────────────────────────────────────────────────┐
│                    DJANGO BACKEND                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  views.py                                             │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │ @transcribe_view (POST /transcribe/)                 │  │
│  │  ├─ Receive audio file                               │  │
│  │  ├─ Save to temp file                                │  │
│  │  ├─ Call Whisper model                               │  │
│  │  ├─ Return transcription                             │  │
│  │  └─ Call mood detection                              │  │
│  │                                                       │  │
│  │ @save_voice_entry (POST /save-voice-entry/)          │  │
│  │  ├─ Parse JSON payload                               │  │
│  │  ├─ Create JournalEntry with mood                    │  │
│  │  └─ Return success/error                             │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  models.py - JournalEntry (Enhanced)                 │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │ • mood: CharField (6 choices)                        │  │
│  │ • mood_confidence: FloatField (0-1)                  │  │
│  │ • sentiment_polarity: FloatField (-1 to 1)           │  │
│  │ • is_voice_entry: BooleanField                       │  │
│  │ • voice_transcript: TextField                        │  │
│  │ • detected_emotions: JSONField                       │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  mood_detector.py - NLP Module                       │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │ • detect_mood(text) → mood, confidence               │  │
│  │ • analyze_text_emotions(text) → full analysis        │  │
│  │ • Dual sentiment approach (Transformer + TextBlob)   │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                      NLP MODELS                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  OpenAI Whisper                                       │  │
│  │  ├─ Audio → Text transcription                        │  │
│  │  └─ Base model (74M parameters)                       │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  DistilBERT (Primary)                                │  │
│  │  ├─ Text → Sentiment (positive/negative)             │  │
│  │  ├─ Fine-tuned on SST-2 dataset                       │  │
│  │  └─ ~92% accuracy                                     │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  TextBlob (Fallback)                                 │  │
│  │  ├─ Text → Polarity (-1 to 1)                        │  │
│  │  └─ Lightweight alternative                          │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                      DATABASE                                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  SQLite (or PostgreSQL)                               │  │
│  │  └─ JournalEntry table with mood metadata            │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## 🎨 UI Layout

```
┌─────────────────────────────────────────────────────────────┐
│                          HEADER                              │
│  🎤 Voice to Text with Mood Detection                        │
│  Record, transcribe, and detect your emotional tone...       │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    RECORDING SECTION                         │
│  🎙️ Recording Controls                                       │
│  [🔴 Start] [⏹️ Stop] [▶️ Play] [Idle]                       │
│                                                              │
│  📂 Or upload audio                                          │
│  [Choose File...]                                            │
│  Supported: MP3, WAV, OGG, M4A                               │
│                                                              │
│  [🚀 Transcribe & Detect Mood (Full Width)]                  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    MOOD DETECTION PANEL                      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 😊 Happy                                            │   │
│  │ Very positive sentiment detected                    │   │
│  │                                                    │   │
│  │ Confidence: 85% [████████░] │ Polarity: 0.72      │   │
│  │                                                    │   │
│  │ Detected Emotions:                                 │   │
│  │ [excited] [grateful] [optimistic]                  │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                  TRANSCRIPTION SECTION                       │
│  📝 Transcription                                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ I'm so happy and excited about this project! It's  │   │
│  │ going great and I'm learning so much.              │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  [Title Input________________]                              │
│                                                              │
│  [💾 Save to Journal] [🗑️ Clear]                            │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                          FOOTER                              │
│  💡 Tips for better results:                                │
│  • Speak clearly and avoid background noise                 │
│  • Use natural speech patterns for accurate mood detection   │
│  • Longer entries provide more accurate mood analysis        │
└─────────────────────────────────────────────────────────────┘
```

## 🔄 Data Flow Diagram

```
User Input (Audio)
      ↓
   ┌──────────────┐
   │ Browser API  │ (getUserMedia / File Input)
   └──────────────┘
      ↓
   [Audio Blob]
      ↓
   ┌──────────────────────┐
   │ FormData with audio  │
   └──────────────────────┘
      ↓
   POST /transcribe/
      ↓
   ┌──────────────────────────────────────┐
   │ Django Backend                       │
   │ ├─ Save to temp file                │
   │ ├─ Call Whisper model               │
   │ └─ Get transcribed text             │
   └──────────────────────────────────────┘
      ↓
   [Transcribed Text]
      ↓
   ┌──────────────────────────────────────┐
   │ Mood Detection Module                │
   │ ├─ Try Transformer (Primary)         │
   │ ├─ Fallback to TextBlob              │
   │ ├─ Calculate confidence              │
   │ ├─ Calculate polarity                │
   │ └─ Detect emotions                   │
   └──────────────────────────────────────┘
      ↓
   [Mood Analysis Result]
      {
        "text": "...",
        "mood": "happy",
        "mood_confidence": 0.85,
        "polarity": 0.72,
        "emoji": "😊",
        "detected_emotions": ["excited", "grateful"]
      }
      ↓
   ┌──────────────────────────────────────┐
   │ Frontend Display                     │
   │ ├─ Update textarea with text         │
   │ ├─ Show mood panel                   │
   │ ├─ Display emoji                     │
   │ ├─ Fill confidence bar               │
   │ └─ Show emotion tags                 │
   └──────────────────────────────────────┘
      ↓
   [User Reviews & Edits]
      ↓
   POST /save-voice-entry/
      ↓
   ┌──────────────────────────────────────┐
   │ Django Backend                       │
   │ ├─ Create JournalEntry object        │
   │ ├─ Store mood data                   │
   │ ├─ Store transcript                  │
   │ └─ Save to database                  │
   └──────────────────────────────────────┘
      ↓
   ┌─────────────────────────┐
   │ Entry in Database ✓     │
   │ {id, mood, emotions...} │
   └─────────────────────────┘
```

## 📊 Mood Detection Logic

```
Text Input
   ↓
┌─────────────────────────────────┐
│  Sentiment Analysis             │
│  ┌───────────────────────────┐ │
│  │ Transformer (Primary)     │ │
│  │ "distilbert-...-sst-2"    │ │
│  │ → Sentiment (Pos/Neg)     │ │
│  │ → Confidence Score        │ │
│  └───────────────────────────┘ │
│           OR                    │
│  ┌───────────────────────────┐ │
│  │ TextBlob (Fallback)       │ │
│  │ → Polarity (-1 to 1)      │ │
│  │ → Subjectivity (0 to 1)   │ │
│  └───────────────────────────┘ │
└─────────────────────────────────┘
   ↓
[Polarity Score: -1 to 1]
   ↓
┌──────────────────────────────────────┐
│ Polarity-to-Mood Mapping             │
├──────────────────────────────────────┤
│ > 0.5     → Happy      😊            │
│ 0.1-0.5   → Optimistic 🙂            │
│ -0.1-0.1  → Neutral    😐            │
│ -0.5--0.1 → Sad        😢            │
│ < -0.5    → Angry      😠            │
└──────────────────────────────────────┘
   ↓
[Primary Mood]
   ↓
┌──────────────────────────────────────┐
│ Emotion Keyword Detection            │
│ Search for keywords:                 │
│ • "excited" → excited                │
│ • "worried" → anxious                │
│ • "tired" → tired                    │
│ • "grateful" → grateful              │
│ • "frustrated" → frustrated          │
└──────────────────────────────────────┘
   ↓
[Primary Mood + Detected Emotions]
   ↓
[Final Result]
{
  mood: "happy",
  confidence: 0.85,
  polarity: 0.72,
  emotions: ["excited", "grateful"]
}
```

## 🎯 Mood Categories

```
😊 HAPPY
├─ Polarity: > 0.5
├─ Confidence: 0.8+
├─ Keywords: love, wonderful, amazing, fantastic
└─ Color: Green

🙂 OPTIMISTIC  
├─ Polarity: 0.1 - 0.5
├─ Confidence: 0.6+
├─ Keywords: hopeful, positive, good, better
└─ Color: Light Green

😐 NEUTRAL
├─ Polarity: -0.1 - 0.1
├─ Confidence: 0.5+
├─ Keywords: okay, normal, regular, standard
└─ Color: Gray

😢 SAD
├─ Polarity: -0.5 - -0.1
├─ Confidence: 0.6+
├─ Keywords: sad, unhappy, disappointed, down
└─ Color: Light Red

😠 ANGRY
├─ Polarity: < -0.5
├─ Confidence: 0.8+
├─ Keywords: angry, furious, hate, frustrated
└─ Color: Red

😰 ANXIOUS
├─ Polarity: Variable
├─ Keywords: worried, nervous, anxious, scared
├─ Emotion Detection
└─ Color: Orange
```

## 📈 Database Schema

```
JournalEntry Table
┌─────────────────────────────────────────┐
│ id (PK)                                 │
├─────────────────────────────────────────┤
│ title: CharField(100)                   │
│ content: TextField                      │
│ mode: CharField(20) - personal/prof.    │
│ created_at: DateTimeField               │
├─────────────────────────────────────────┤
│ MOOD DETECTION FIELDS (NEW):            │
├─────────────────────────────────────────┤
│ mood: CharField(20) - 6 choices         │
│ mood_confidence: FloatField (0-1)       │
│ sentiment_polarity: FloatField (-1-1)   │
│ detected_emotions: JSONField            │
├─────────────────────────────────────────┤
│ VOICE ENTRY FIELDS (NEW):               │
├─────────────────────────────────────────┤
│ is_voice_entry: BooleanField            │
│ voice_transcript: TextField             │
└─────────────────────────────────────────┘
```

## 🔧 File Structure

```
echojournal/
├── dashboard/
│   ├── models.py ✏️ (Enhanced)
│   ├── views.py ✏️ (Enhanced)
│   ├── urls.py ✏️ (Enhanced)
│   ├── templates/
│   │   └── dashboard/
│   │       └── voice.html 📝 (New/Completely Redesigned)
│   └── migrations/
│       └── 0002_voice_mood_detection.py 📝 (New)
│
├── echoapp/
│   └── nlp_module/
│       ├── mood_detector.py 📝 (New)
│       ├── engine.py (Existing)
│       └── tones.py (Existing)
│
├── VOICE_MOOD_DETECTION_README.md 📝 (New)
├── SETUP_VOICE_MOOD.md 📝 (New)
├── VOICE_MOOD_CODE_EXAMPLES.md 📝 (New)
├── IMPLEMENTATION_SUMMARY.md 📝 (New)
├── voice_mood_requirements.txt 📝 (New)
├── VOICE_MOOD_SETUP_CHECKLIST.md 📝 (New)
└── VOICE_MOOD_VISUAL_GUIDE.md 📝 (This File)

Legend: ✏️ = Modified, 📝 = New
```

## ✨ Key Features Summary

```
┌──────────────────────────┐
│  RECORDING & UPLOAD      │
├──────────────────────────┤
│ ✓ Microphone Recording   │
│ ✓ File Upload            │
│ ✓ Audio Preview          │
│ ✓ Status Display         │
└──────────────────────────┘

┌──────────────────────────┐
│  TRANSCRIPTION           │
├──────────────────────────┤
│ ✓ Whisper AI Model       │
│ ✓ High Accuracy          │
│ ✓ Multiple Formats       │
│ ✓ Error Handling         │
└──────────────────────────┘

┌──────────────────────────┐
│  MOOD DETECTION          │
├──────────────────────────┤
│ ✓ 6 Mood Categories      │
│ ✓ Confidence Scoring     │
│ ✓ Polarity Analysis      │
│ ✓ Emotion Keywords       │
│ ✓ Emoji Representation   │
└──────────────────────────┘

┌──────────────────────────┐
│  DATABASE STORAGE        │
├──────────────────────────┤
│ ✓ Full Entry Storage     │
│ ✓ Mood Metadata          │
│ ✓ Emotion Tracking       │
│ ✓ Analytics Ready        │
└──────────────────────────┘

┌──────────────────────────┐
│  USER EXPERIENCE         │
├──────────────────────────┤
│ ✓ Responsive Design      │
│ ✓ Real-time Feedback     │
│ ✓ Clear Indicators       │
│ ✓ Mobile Friendly        │
│ ✓ Smooth Animations      │
└──────────────────────────┘
```

---

This visual guide complements the technical documentation and helps understand the feature at a glance.
