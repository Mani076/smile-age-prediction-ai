"""
Pydantic schemas for request/response validation
"""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


# Enums
class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


class EmotionType(str, Enum):
    HAPPY = "Happy"
    SAD = "Sad"
    ANGRY = "Angry"
    NEUTRAL = "Neutral"
    FEAR = "Fear"
    SURPRISE = "Surprise"
    DISGUST = "Disgust"


# Auth Schemas
class UserRegister(BaseModel):
    first_name: str = Field(..., min_length=2, max_length=50)
    last_name: str = Field(..., min_length=2, max_length=50)
    phone_number: Optional[str] = None
    email: EmailStr
    password: str = Field(..., min_length=8)
    confirm_password: Optional[str] = None

    @validator('password')
    def validate_password(cls, v):
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')
        if not any(char.isupper() for char in v):
            raise ValueError('Password must contain at least one uppercase letter')
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None
    email: Optional[str] = None
    role: Optional[str] = None


# User Schemas
class UserBase(BaseModel):
    first_name: str
    last_name: str
    phone: Optional[str] = None
    email: EmailStr


class UserResponse(UserBase):
    id: int
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None


# Prediction Schemas
class FaceDetection(BaseModel):
    face_id: int
    age: Optional[int] = None
    age_range: str
    smile: bool
    smile_confidence: float = Field(..., ge=0, le=1)
    emotion: str
    emotion_confidence: float = Field(..., ge=0, le=1)
    bounding_box: dict


class PredictionResponse(BaseModel):
    prediction_id: int
    num_faces: int
    faces: List[FaceDetection]
    processing_time: float
    model_version: str
    created_at: datetime

    class Config:
        from_attributes = True


class PredictionHistory(BaseModel):
    id: int
    image_path: str
    num_faces: int
    avg_age: Optional[float]
    smile_count: int
    dominant_emotion: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# Model Management Schemas
class ModelMetrics(BaseModel):
    accuracy: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1_score: Optional[float] = None


class ModelResponse(BaseModel):
    id: int
    version: str
    model_type: str
    is_active: bool
    accuracy: Optional[float]
    precision: Optional[float]
    recall: Optional[float]
    f1_score: Optional[float]
    created_at: datetime

    class Config:
        from_attributes = True


# Analytics Schemas
class EmotionDistribution(BaseModel):
    emotion: str
    count: int
    percentage: float


class AnalyticsSummary(BaseModel):
    total_predictions: int
    total_faces_detected: int
    avg_age: float
    smile_percentage: float
    emotion_distribution: List[EmotionDistribution]
    predictions_today: int
    predictions_this_week: int
    predictions_this_month: int


class DailyStats(BaseModel):
    date: str
    prediction_count: int
    avg_age: float
    smile_percentage: float


# Report Schemas
class ReportRequest(BaseModel):
    prediction_id: int


class ReportResponse(BaseModel):
    report_id: int
    pdf_path: str
    file_size: int
    created_at: datetime

    class Config:
        from_attributes = True


# Admin Schemas
class AdminUserList(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str
    role: str
    is_active: bool
    prediction_count: int
    created_at: datetime


class SystemStats(BaseModel):
    total_users: int
    active_users: int
    total_predictions: int
    total_reports: int
    avg_predictions_per_user: float
    storage_used_mb: float