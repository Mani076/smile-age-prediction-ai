"""
Analytics routes for statistics and insights
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from typing import List

from ..database import get_db
from ..models import User, Prediction
from ..schemas import AnalyticsSummary, EmotionDistribution, DailyStats
from ..auth.dependencies import get_current_user

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get("/summary", response_model=AnalyticsSummary)
async def get_analytics_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive analytics summary for current user
    
    Includes:
    - Total predictions
    - Total faces detected
    - Average age
    - Smile percentage
    - Emotion distribution
    - Time-based statistics
    """
    # Get all user predictions
    predictions = db.query(Prediction)\
        .filter(Prediction.user_id == current_user.id)\
        .all()
    
    total_predictions = len(predictions)
    total_faces = sum(p.num_faces for p in predictions)
    
    # Calculate average age
    ages = [p.avg_age for p in predictions if p.avg_age is not None]
    avg_age = sum(ages) / len(ages) if ages else 0
    
    # Calculate smile percentage
    total_smiles = sum(p.smile_count for p in predictions)
    smile_percentage = (total_smiles / total_faces * 100) if total_faces > 0 else 0
    
    # Emotion distribution
    emotion_counts = {}
    for prediction in predictions:
        for face in prediction.faces_data:
            emotion = face.get("emotion", "Unknown")
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
    
    emotion_distribution = [
        {
            "emotion": emotion,
            "count": count,
            "percentage": round(count / total_faces * 100, 2) if total_faces > 0 else 0
        }
        for emotion, count in emotion_counts.items()
    ]
    
    # Time-based statistics
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=7)
    month_start = now - timedelta(days=30)
    
    predictions_today = db.query(Prediction)\
        .filter(
            Prediction.user_id == current_user.id,
            Prediction.created_at >= today_start
        )\
        .count()
    
    predictions_this_week = db.query(Prediction)\
        .filter(
            Prediction.user_id == current_user.id,
            Prediction.created_at >= week_start
        )\
        .count()
    
    predictions_this_month = db.query(Prediction)\
        .filter(
            Prediction.user_id == current_user.id,
            Prediction.created_at >= month_start
        )\
        .count()
    
    return {
        "total_predictions": total_predictions,
        "total_faces_detected": total_faces,
        "avg_age": round(avg_age, 1),
        "smile_percentage": round(smile_percentage, 1),
        "emotion_distribution": emotion_distribution,
        "predictions_today": predictions_today,
        "predictions_this_week": predictions_this_week,
        "predictions_this_month": predictions_this_month
    }


@router.get("/trends", response_model=List[DailyStats])
async def get_daily_trends(
    days: int = Query(default=7, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get daily prediction trends
    
    - **days**: Number of days to retrieve (1-90)
    """
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Get predictions grouped by date
    predictions = db.query(Prediction)\
        .filter(
            Prediction.user_id == current_user.id,
            Prediction.created_at >= start_date
        )\
        .all()
    
    # Group by date
    daily_data = {}
    for prediction in predictions:
        date_key = prediction.created_at.date().isoformat()
        
        if date_key not in daily_data:
            daily_data[date_key] = {
                "date": date_key,
                "prediction_count": 0,
                "total_age": 0,
                "age_count": 0,
                "total_smiles": 0,
                "total_faces": 0
            }
        
        daily_data[date_key]["prediction_count"] += 1
        daily_data[date_key]["total_faces"] += prediction.num_faces
        daily_data[date_key]["total_smiles"] += prediction.smile_count
        
        if prediction.avg_age:
            daily_data[date_key]["total_age"] += prediction.avg_age
            daily_data[date_key]["age_count"] += 1
    
    # Calculate averages
    result = []
    for data in daily_data.values():
        avg_age = data["total_age"] / data["age_count"] if data["age_count"] > 0 else 0
        smile_pct = (data["total_smiles"] / data["total_faces"] * 100) if data["total_faces"] > 0 else 0
        
        result.append({
            "date": data["date"],
            "prediction_count": data["prediction_count"],
            "avg_age": round(avg_age, 1),
            "smile_percentage": round(smile_pct, 1)
        })
    
    # Sort by date
    result.sort(key=lambda x: x["date"])
    
    return result


@router.get("/emotion-breakdown")
async def get_emotion_breakdown(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed emotion breakdown with confidence scores"""
    predictions = db.query(Prediction)\
        .filter(Prediction.user_id == current_user.id)\
        .all()
    
    emotion_data = {}
    
    for prediction in predictions:
        for face in prediction.faces_data:
            emotion = face.get("emotion", "Unknown")
            confidence = face.get("emotion_confidence", 0)
            
            if emotion not in emotion_data:
                emotion_data[emotion] = {
                    "count": 0,
                    "total_confidence": 0,
                    "confidences": []
                }
            
            emotion_data[emotion]["count"] += 1
            emotion_data[emotion]["total_confidence"] += confidence
            emotion_data[emotion]["confidences"].append(confidence)
    
    # Calculate statistics
    result = []
    for emotion, data in emotion_data.items():
        avg_confidence = data["total_confidence"] / data["count"]
        min_confidence = min(data["confidences"])
        max_confidence = max(data["confidences"])
        
        result.append({
            "emotion": emotion,
            "count": data["count"],
            "avg_confidence": round(avg_confidence, 3),
            "min_confidence": round(min_confidence, 3),
            "max_confidence": round(max_confidence, 3)
        })
    
    # Sort by count
    result.sort(key=lambda x: x["count"], reverse=True)
    
    return {"emotions": result}


@router.get("/age-distribution")
async def get_age_distribution(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get age range distribution"""
    predictions = db.query(Prediction)\
        .filter(Prediction.user_id == current_user.id)\
        .all()
    
    age_ranges = {}
    
    for prediction in predictions:
        for face in prediction.faces_data:
            age_range = face.get("age_range", "Unknown")
            age_ranges[age_range] = age_ranges.get(age_range, 0) + 1
    
    result = [
        {"age_range": range_name, "count": count}
        for range_name, count in age_ranges.items()
    ]
    
    # Sort by age range
    range_order = ["0-12", "13-18", "19-25", "26-35", "36-45", "46-60", "61+"]
    result.sort(key=lambda x: range_order.index(x["age_range"]) if x["age_range"] in range_order else 999)
    
    return {"age_ranges": result}
