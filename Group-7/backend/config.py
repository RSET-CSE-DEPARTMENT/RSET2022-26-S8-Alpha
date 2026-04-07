from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # ── Friend's AI server (ngrok URL — update whenever it changes) ──
    ngrok_base_url: str = ""          # e.g. https://xxxx-xx-xx.ngrok-free.app

    # ── TTS Settings ──
    tts_voice: str = "en-US-GuyNeural"

    # ── Whisper / ASR Settings ──
    whisper_model_path: str = r"C:\whisper_models\small"
    whisper_device: str = "cuda"
    whisper_compute_type: str = "float16"

    # ── Server ──
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    frontend_origin: str = "http://localhost:5173"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
