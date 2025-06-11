"""
Application configuration settings.

This module contains all the configuration settings for the application,
including API keys, database URLs, and other environment-specific settings.
"""
import os
from typing import Dict, List, Optional, Union, Any
from typing import List, Optional
from pydantic import HttpUrl, PostgresDsn, field_validator, ConfigDict, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict, PydanticBaseSettingsSource
from typing import Tuple, Any, Dict, List, Optional, Union
import json
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    """Application settings."""
    
    # Application
    APP_NAME: str = "coBoarding"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "insecure-secret-key-change-me")
    API_PREFIX: str = "/api"
    
    # Supported Languages - Handle as string in env and convert to list
    SUPPORTED_LANGUAGES_STR: str = os.getenv("SUPPORTED_LANGUAGES", "en,pl,de")
    
    @property
    def SUPPORTED_LANGUAGES(self) -> List[str]:
        """Get the supported languages as a list."""
        return [lang.strip() for lang in self.SUPPORTED_LANGUAGES_STR.split(",") if lang.strip()] or ["en", "pl", "de"]
    
    # API Keys
    API_KEY: str = os.getenv("API_KEY", "test-api-key")
    ADMIN_API_KEY: str = os.getenv("ADMIN_API_KEY", "test-admin-api-key")
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:8000",
        "http://localhost:3000",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:3000"
    ]
    
    # AI and LLM Settings
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    FORM_ANALYZER_MODEL: str = os.getenv("FORM_ANALYZER_MODEL", "llama3")
    CV_PARSER_MODEL: str = os.getenv("CV_PARSER_MODEL", "llama3")
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "sqlite:///./sql_app.db"
    )
    
    # LLM Configuration
    LLM_API_BASE: str = os.getenv("LLM_API_BASE", "http://localhost:11434")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "llama2")
    FORM_ANALYZER_MODEL: str = os.getenv("FORM_ANALYZER_MODEL", "llama2")
    
    # File Uploads
    UPLOAD_FOLDER: str = os.getenv("UPLOAD_FOLDER", "./uploads")
    MAX_CONTENT_LENGTH: int = int(os.getenv("MAX_CONTENT_LENGTH", "16777216"))  # 16MB
    ALLOWED_EXTENSIONS: set = {"pdf", "docx", "doc", "txt"}
    
    # Browser Automation
    BROWSER_HEADLESS: bool = os.getenv("BROWSER_HEADLESS", "False").lower() in ("true", "1", "t")
    BROWSER_SLOW_MO: int = int(os.getenv("BROWSER_SLOW_MO", "100"))  # milliseconds
    
    # Rate Limiting
    RATE_LIMIT: str = os.getenv("RATE_LIMIT", "100/minute")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv(
        "LOG_FORMAT", 
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Security
    SECURITY_PASSWORD_SALT: str = os.getenv("SECURITY_PASSWORD_SALT", "insecure-salt-change-me")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 hours
    
    @field_validator('BACKEND_CORS_ORIGINS', mode='before')
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith('[') and v.endswith(']'):
                # Handle JSON array string
                import json
                return json.loads(v)
            # Handle comma-separated string
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return [
            "http://localhost:8000",
            "http://localhost:3000",
            "http://127.0.0.1:8000",
            "http://127.0.0.1:3000"
        ]
    
    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        env_file_encoding='utf-8',
        extra='ignore',
        env_nested_delimiter='__',
        env_prefix='',
        env_ignore_empty=True,
        validate_default=True,
        arbitrary_types_allowed=True
    )

# Create settings instance
settings = Settings()

# Ensure upload folder exists
os.makedirs(settings.UPLOAD_FOLDER, exist_ok=True)
