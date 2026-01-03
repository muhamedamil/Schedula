import os
from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # ---- Environment ----
    ENV: str = Field(default="development", env="ENV")
    
    # ---- LLM ----
    GROQ_API_KEY: str = Field(..., env="GROQ_API_KEY")
    GROQ_MODEL_NAME: str = Field(default="llama-3.1-8b-instant", env="GROQ_MODEL_NAME")
    GROQ_TEMPERATURE: float = Field(default=0.0, env="GROQ_TEMPERATURE")
    GROQ_MAX_TOKENS: int = Field(default=512, env="GROQ_MAX_TOKENS")
    GROQ_TOP_P: float = Field(default=1.0, env="GROQ_TOP_P")

    # ---- LLM Runtime ----
    LLM_REQUEST_TIMEOUT: int = Field(default=8, env="LLM_REQUEST_TIMEOUT")
    LLM_MAX_RETRIES: int = Field(default=2, env="LLM_MAX_RETRIES")

    # ---- STT ----
    WHISPER_MODEL: str = Field(default="small", env="WHISPER_MODEL")
    WHISPER_LANGUAGE: str = Field(default="en", env="WHISPER_LANGUAGE")
    WHISPER_COMPUTE_TYPE: str = Field(default="int8", env="WHISPER_COMPUTE_TYPE")
    STT_SAMPLE_RATE: int = Field(default=16000, env="STT_SAMPLE_RATE")

    # ---- TTS ----
    TTS_PROVIDER: str = Field(default="kokoro", env="TTS_PROVIDER")
    TTS_VOICE: str = Field(default="af_heart", env="TTS_VOICE")
    TTS_SAMPLE_RATE: int = Field(default=24000, env="TTS_SAMPLE_RATE")

    # ---- Calendar ----
    GOOGLE_CLIENT_ID: str = Field(..., env="GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: str = Field(..., env="GOOGLE_CLIENT_SECRET")
    GOOGLE_REFRESH_TOKEN: str = Field(..., env="GOOGLE_REFRESH_TOKEN")
    GOOGLE_CALENDAR_ID: str = Field(default="primary", env="GOOGLE_CALENDAR_ID")

    # ---- App / Deployment ----
    APP_HOST: str = Field(default="0.0.0.0", env="APP_HOST")
    APP_PORT: int = Field(default=8000, env="APP_PORT")
    DEBUG: bool = Field(default=True, env="DEBUG")

    # ---- Logging ----
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FILE_PATH: str = Field(default="app.log", env="LOG_FILE_PATH")

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
