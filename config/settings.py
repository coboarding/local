import os
from pydantic import BaseSettings
from typing import Dict, List

class Settings(BaseSettings):
    # Database
    REDIS_URL: str = "redis://localhost:6379"
    DATA_TTL_HOURS: int = 24
    
    # AI Models
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    CV_PARSER_MODEL: str = "llava:7b"
    FORM_ANALYZER_MODEL: str = "mistral:7b"
    
    # Integrations
    LINKEDIN_CLIENT_ID: str
    LINKEDIN_CLIENT_SECRET: str
    SLACK_BOT_TOKEN: str
    TEAMS_WEBHOOK_URL: str
    GMAIL_CLIENT_ID: str
    GMAIL_CLIENT_SECRET: str
    WHATSAPP_TOKEN: str
    
    # Business Model
    MONTHLY_SUBSCRIPTION_USD: float = 50.0
    PER_CANDIDATE_USD: float = 10.0
    
    # Supported Languages
    SUPPORTED_LANGUAGES: List[str] = ["en", "pl", "de"]
    
    # Security
    SECRET_KEY: str
    API_KEY: str
    
    class Config:
        env_file = ".env"

settings = Settings()