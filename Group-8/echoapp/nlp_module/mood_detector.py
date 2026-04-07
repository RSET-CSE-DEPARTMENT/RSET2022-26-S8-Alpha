"""
Mood Detection Module
Analyzes text to detect emotional tone and mood
"""

from textblob import TextBlob
import logging

logger = logging.getLogger(__name__)

# Try to load the transformer-based sentiment model
USE_TRANSFORMER = False
try:
    from transformers import pipeline
    sentiment_pipeline = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")
    USE_TRANSFORMER = True
except Exception as e:
    logger.warning(f"Could not load transformer model: {e}. Using TextBlob only.")
    sentiment_pipeline = None


def detect_mood(text):
    """
    Detects mood from TRANSCRIBED TEXT using sentiment analysis.
    
    IMPORTANT: This analyzes the WORDS and CONTENT of speech (after transcription),
    NOT the acoustic features like tone, pitch, or voice quality.
    
    For voice tone analysis, acoustic feature extraction would be needed
    (pitch, energy, speaking rate, etc.) which is not implemented here.
    
    Args:
        text (str): The transcribed text to analyze
        
    Returns:
        dict: {
            'mood': 'happy'|'sad'|'neutral'|'angry'|'anxious'|'optimistic',
            'confidence': float (0-1),
            'polarity': float (-1 to 1),
            'description': str
        }
    """
    if not text or not isinstance(text, str):
        return {
            'mood': 'neutral',
            'confidence': 0.0,
            'polarity': 0.0,
            'description': 'No text provided'
        }
    
    text_lower = text.lower()
    
    # Enhanced keyword-based detection for different negative emotions
    anger_indicators = ['angry', 'furious', 'hate', 'rage', 'mad', 'pissed', 'disgusted', 'infuriated', 'outraged', 'livid']
    sadness_indicators = ['sad', 'depressed', 'crying', 'tears', 'heartbroken', 'miserable', 'devastated', 'grief', 'sorrow']
    anxiety_indicators = ['anxious', 'worried', 'nervous', 'stressed', 'panic', 'fear', 'scared', 'afraid', 'tense']
    
    has_anger = any(word in text_lower for word in anger_indicators)
    has_sadness = any(word in text_lower for word in sadness_indicators)
    has_anxiety = any(word in text_lower for word in anxiety_indicators)
    
    # Method 1: Transformer-based (more accurate)
    if USE_TRANSFORMER:
        try:
            result = sentiment_pipeline(text[:512])[0]  # Limit to 512 tokens
            label = result['label'].lower()
            score = result['score']
            
            mood = 'positive' if label == 'positive' else 'negative'
            polarity = score if label == 'positive' else -score
            
            # Override with keyword detection if strong indicators present
            if has_anger and polarity < 0:
                polarity = min(polarity - 0.3, -0.7)  # Strong anger signal
            elif has_sadness and polarity < 0:
                polarity = max(polarity, -0.5)  # Moderate sad signal
            elif has_anxiety:
                polarity = min(polarity - 0.2, -0.3)  # Anxiety signal
            
            return _map_sentiment_to_mood(polarity, score)
        except Exception as e:
            logger.warning(f"Transformer analysis failed: {e}")
    
    # Method 2: TextBlob fallback (lighter weight) with enhancements
    try:
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity  # -1 to 1
        subjectivity = blob.sentiment.subjectivity  # 0 to 1
        
        # Boost detection based on specific emotion keywords
        if has_anger and polarity < 0:
            polarity = min(polarity - 0.3, -0.7)  # Strong anger detection
        elif has_sadness and polarity < 0:
            polarity = min(polarity - 0.15, -0.4)  # Sad detection
        elif has_anxiety:
            polarity = max(min(polarity - 0.2, -0.2), -0.4)  # Anxiety range
        
        # Calculate confidence: higher for subjective text
        confidence = 0.5 + (subjectivity * 0.5) + (abs(polarity) * 0.3)
        confidence = min(1.0, confidence)
        
        return _map_sentiment_to_mood(polarity, confidence)
    except Exception as e:
        logger.error(f"Mood detection failed: {e}")
        return {
            'mood': 'neutral',
            'confidence': 0.0,
            'polarity': 0.0,
            'description': 'Error analyzing mood'
        }


def _map_sentiment_to_mood(polarity, confidence):
    """
    Maps sentiment polarity to mood categories with improved thresholds.
    Enhanced for better sad emotion detection with expanded negative range.
    
    Args:
        polarity (float): Sentiment polarity (-1 to 1)
        confidence (float): Confidence score (0 to 1)
        
    Returns:
        dict: Mood information
    """
    # Ensure polarity is in range
    polarity = max(-1, min(1, polarity))
    
    # Improved thresholds for better mood distinction
    if polarity > 0.6:
        mood = 'happy'
        description = 'Very positive sentiment detected'
        confidence_multiplier = 1.2
    elif polarity > 0.15:
        mood = 'optimistic'
        description = 'Positive sentiment detected'
        confidence_multiplier = 1.0
    elif polarity > -0.15:
        mood = 'neutral'
        description = 'Neutral sentiment detected'
        confidence_multiplier = 0.8
    elif polarity > -0.35:
        # Mildly negative - could be anxious or sad
        mood = 'anxious'
        description = 'Anxious or worried sentiment detected'
        confidence_multiplier = 1.0
    elif polarity > -0.55:
        # Moderately negative - sad
        mood = 'sad'
        description = 'Sad or disappointed sentiment detected'
        confidence_multiplier = 1.1
    elif polarity > -0.75:
        # Very negative - could be angry or very sad
        mood = 'angry'
        description = 'Strong negative sentiment detected (anger likely)'
        confidence_multiplier = 1.15
    else:
        # Extremely negative - definitely angry
        mood = 'angry'
        description = 'Very strong negative sentiment detected (high anger)'
        confidence_multiplier = 1.3
    
    # Calculate final confidence with multiplier
    final_confidence = min(1.0, abs(polarity) * confidence_multiplier * confidence)
    
    return {
        'mood': mood,
        'confidence': final_confidence,
        'polarity': polarity,
        'description': description
    }


def get_mood_emoji(mood):
    """Returns an emoji representation of the mood"""
    emoji_map = {
        'happy': '😊',
        'optimistic': '🙂',
        'neutral': '😐',
        'sad': '😢',
        'angry': '😠',
        'anxious': '😰',
        'positive': '😊',
        'negative': '😢'
    }
    return emoji_map.get(mood, '😐')


def analyze_text_emotions(text):
    """
    Comprehensive emotion analysis of text.
    Detects multiple emotional indicators from transcribed speech.
    
    NOTE: This analyzes TRANSCRIBED TEXT content, not voice tone.
    Whisper converts speech to text, then we analyze the words/sentences.
    
    Args:
        text (str): Text to analyze
        
    Returns:
        dict: Comprehensive emotion analysis with 15+ detectable emotions
    """
    mood_result = detect_mood(text)
    
    # Enhanced emotion keywords with more patterns
    # Total: 15 distinct emotions can be detected
    emotion_keywords = {
        # Positive emotions (5)
        'excited': ['excited', 'thrilled', 'amazing', 'wonderful', 'fantastic', 'awesome', 'incredible', 'ecstatic', 'pumped'],
        'joyful': ['joyful', 'happy', 'delighted', 'cheerful', 'pleased', 'glad', 'content', 'elated'],
        'grateful': ['grateful', 'thankful', 'appreciate', 'blessed', 'lucky', 'thank you', 'thanks', 'fortunate'],
        'proud': ['proud', 'accomplished', 'achieved', 'succeeded', 'victory', 'won', 'nailed it'],
        'hopeful': ['hopeful', 'optimistic', 'looking forward', 'positive', 'confident', 'bright future'],
        
        # Negative emotions (6)
        'angry': ['angry', 'furious', 'enraged', 'mad', 'pissed', 'outraged', 'livid', 'hate', 'hate this', 'disgusted', 'infuriated', 'rage'],
        'sad': ['sad', 'depressed', 'unhappy', 'miserable', 'heartbroken', 'crying', 'tears', 'sorrow', 'grief', 'devastated', 'down', 'blue'],
        'anxious': ['worried', 'anxious', 'nervous', 'stressed', 'afraid', 'scared', 'terrified', 'panic', 'fear', 'uneasy', 'tense'],
        'frustrated': ['frustrated', 'annoyed', 'irritated', 'fed up', 'bothered', 'aggravated', 'exasperated', 'tired of'],
        'disappointed': ['disappointed', 'let down', 'failed', 'missed', 'regret', 'wish', 'should have', 'could have'],
        'lonely': ['lonely', 'alone', 'isolated', 'abandoned', 'nobody', 'no one', 'missing', 'empty'],
        
        # Neutral/Other emotions (4)
        'tired': ['tired', 'exhausted', 'weary', 'fatigued', 'sleepy', 'drained', 'worn out', 'beat'],
        'confused': ['confused', 'puzzled', 'bewildered', "don't understand", 'lost', 'unclear', 'uncertain'],
        'surprised': ['surprised', 'shocked', 'amazed', 'astonished', 'unexpected', 'wow', 'oh my'],
        'calm': ['calm', 'peaceful', 'relaxed', 'serene', 'tranquil', 'at ease', 'composed']
    }
    
    text_lower = text.lower()
    detected_emotions = []
    emotion_counts = {}
    
    # Count keyword matches for each emotion (for confidence weighting)
    for emotion, keywords in emotion_keywords.items():
        match_count = sum(1 for keyword in keywords if keyword in text_lower)
        if match_count > 0:
            detected_emotions.append(emotion)
            emotion_counts[emotion] = match_count
    
    # Sort emotions by match count (most prominent first)
    detected_emotions.sort(key=lambda e: emotion_counts.get(e, 0), reverse=True)
    
    # Boost primary mood confidence if matching emotions are detected
    confidence_boost = 0
    if mood_result['mood'] == 'angry' and 'angry' in detected_emotions:
        confidence_boost = 0.2
    elif mood_result['mood'] == 'sad' and 'sad' in detected_emotions:
        confidence_boost = 0.2
    elif mood_result['mood'] == 'anxious' and 'anxious' in detected_emotions:
        confidence_boost = 0.15
    elif mood_result['mood'] == 'happy' and ('joyful' in detected_emotions or 'excited' in detected_emotions):
        confidence_boost = 0.15
    
    adjusted_confidence = min(1.0, mood_result['confidence'] + confidence_boost)
    
    return {
        'primary_mood': mood_result['mood'],
        'mood_confidence': adjusted_confidence,
        'polarity': mood_result['polarity'],
        'description': mood_result['description'],
        'detected_emotions': detected_emotions[:5],  # Return top 5 emotions
        'all_emotions': detected_emotions,  # All detected emotions
        'emotion_intensity': emotion_counts,  # How many keywords matched
        'total_emotions_detected': len(detected_emotions),
        'emoji': get_mood_emoji(mood_result['mood']),
        'detection_method': 'text-based (transcribed speech content)'
    }
