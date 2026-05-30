"""
Configuration management for the application
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application
    APP_NAME: str = "AI Image Analysis Tool"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_SECRET_KEY: str = "your-jwt-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Database (using SQLite for simplicity)
    DATABASE_URL: str = "sqlite:///./ai_image_analysis.db"
    
    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://localhost:5000"
    
    @property
    def cors_origins_list(self) -> list:
        """Convert CORS_ORIGINS string to list"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    # File Upload
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE: int = 10485760  # 10MB
    ALLOWED_EXTENSIONS: str = ".jpg,.jpeg,.png,.webp"
    
    @property
    def allowed_extensions_set(self) -> set:
        """Convert ALLOWED_EXTENSIONS string to set"""
        return {ext.strip() for ext in self.ALLOWED_EXTENSIONS.split(",")}
    
    # ML Models
    MODEL_DIR: str = "ml_models"
    AGE_MODEL_PATH: str = "ml_models/age_model.h5"
    SMILE_MODEL_PATH: str = "ml_models/smile_model.h5"
    EMOTION_MODEL_PATH: str = "ml_models/emotion_model.h5"
    FACE_CASCADE_PATH: str = "ml_models/haarcascade_frontalface_default.xml"
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


def get_settings() -> Settings:
    """Get settings instance — no cache so .env is always read fresh"""
    return Settings()
