from pydantic_settings import BaseSettings
from pathlib import Path

class DravionConfig(BaseSettings):
    # --- LLM ---
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_model: str = "gemma"

    # --- API Keys ---
    google_api_key: str = ""
    gemini_api_key: str = ""
    groq_api_key: str = ""
    openrouter_api_key: str = ""

    # --- Voice (dormant) ---
    picovoice_access_key: str = ""
    stt_engine: str = "google_free"
    stt_language: str = "en-US"

    # --- Integrations (dormant) ---
    weather_api_key: str = ""
    serpapi_key: str = ""
    github_token: str = ""

    # --- Paths ---
    data_dir: str = "data"

    # --- System ---
    log_level: str = "INFO"
    voice_enabled: bool = False   # Off until voice module is real
    vision_enabled: bool = False  # Off until vision module is real
    wake_word: str = "dravion"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

config = DravionConfig()

# Ensure data directories exist
Path(config.data_dir).mkdir(exist_ok=True)
