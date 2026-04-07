import sounddevice as sd
import numpy as np
import whisper
import scipy.io.wavfile as wav

DURATION = 5  # seconds
SAMPLE_RATE = 16000  # Whisper prefers 16 kHz

print("🎤 Recording... Speak now!")
audio = sd.rec(int(DURATION * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='float32')
sd.wait()
print("✅ Recording complete.")

# Save recorded audio
wav.write("recorded.wav", SAMPLE_RATE, (audio * 32767).astype(np.int16))

# Load Whisper model
model = whisper.load_model("medium.en")

# Transcribe
result = model.transcribe("recorded.wav")
print("\n🗣️ Transcription:")
print(result["text"])