from faster_whisper import WhisperModel

model = WhisperModel(
    r"C:\whisper_models\small",
    device="cuda",
    compute_type="float16"
)

print("Model loaded successfully.")
