"""
Admin routes for system management
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List
from pathlib import Path

from ..database import get_db
from ..models import User, Prediction, Report, APILog
from ..schemas import AdminUserList, SystemStats
from ..auth.dependencies import get_current_admin

router = APIRouter(prefix="/api/admin", tags=["Admin"])


@router.get("/users", response_model=List[AdminUserList])
async def list_all_users(
    skip: int = 0,
    limit: int = 50,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get list of all users with statistics
    
    Admin only
    """
    # Query users with prediction count
    users = db.query(
        User,
        func.count(Prediction.id).label('prediction_count')
    )\
    .outerjoin(Prediction)\
    .group_by(User.id)\
    .order_by(desc(User.created_at))\
    .offset(skip)\
    .limit(limit)\
    .all()
    
    result = []
    for user, pred_count in users:
        result.append({
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role,
            "is_active": user.is_active,
            "prediction_count": pred_count,
            "created_at": user.created_at
        })
    
    return result


@router.get("/predictions")
async def list_all_predictions(
    skip: int = 0,
    limit: int = 50,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get list of all predictions across all users
    
    Admin only
    """
    predictions = db.query(Prediction)\
        .order_by(desc(Prediction.created_at))\
        .offset(skip)\
        .limit(limit)\
        .all()
    
    result = []
    for pred in predictions:
        user = db.query(User).filter(User.id == pred.user_id).first()
        result.append({
            "id": pred.id,
            "user_email": user.email if user else "Unknown",
            "num_faces": pred.num_faces,
            "avg_age": pred.avg_age,
            "smile_count": pred.smile_count,
            "dominant_emotion": pred.dominant_emotion,
            "created_at": pred.created_at
        })
    
    return result


@router.delete("/predictions/{prediction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prediction_admin(
    prediction_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Delete any prediction (admin only)
    
    Use for removing inappropriate content
    """
    prediction = db.query(Prediction).filter(Prediction.id == prediction_id).first()
    
    if not prediction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prediction not found"
        )
    
    # Delete image file
    image_path = Path(prediction.image_path)
    if image_path.exists():
        image_path.unlink()
    
    # Delete from database
    db.delete(prediction)
    db.commit()
    
    return None


@router.put("/users/{user_id}/toggle-active")
async def toggle_user_active(
    user_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Toggle user active status"""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account"
        )
    
    user.is_active = not user.is_active
    db.commit()
    
    return {
        "user_id": user.id,
        "is_active": user.is_active,
        "message": f"User {'activated' if user.is_active else 'deactivated'}"
    }


@router.get("/stats", response_model=SystemStats)
async def get_system_stats(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive system statistics
    
    Admin only
    """
    # User statistics
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    
    # Prediction statistics
    total_predictions = db.query(Prediction).count()
    
    # Report statistics
    total_reports = db.query(Report).count()
    
    # Average predictions per user
    avg_predictions = total_predictions / total_users if total_users > 0 else 0
    
    # Calculate storage used
    upload_dir = Path("uploads")
    reports_dir = Path("reports")
    
    storage_bytes = 0
    if upload_dir.exists():
        storage_bytes += sum(f.stat().st_size for f in upload_dir.rglob('*') if f.is_file())
    if reports_dir.exists():
        storage_bytes += sum(f.stat().st_size for f in reports_dir.rglob('*') if f.is_file())
    
    storage_mb = storage_bytes / (1024 * 1024)
    
    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_predictions": total_predictions,
        "total_reports": total_reports,
        "avg_predictions_per_user": round(avg_predictions, 2),
        "storage_used_mb": round(storage_mb, 2)
    }


@router.get("/api-logs")
async def get_api_logs(
    skip: int = 0,
    limit: int = 100,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get API usage logs
    
    Admin only
    """
    logs = db.query(APILog)\
        .order_by(desc(APILog.created_at))\
        .offset(skip)\
        .limit(limit)\
        .all()
    
    return logs


@router.get("/dashboard")
async def get_admin_dashboard(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive admin dashboard data
    
    Includes recent activity, top users, and system health
    """
    # Recent predictions
    recent_predictions = db.query(Prediction)\
        .order_by(desc(Prediction.created_at))\
        .limit(10)\
        .all()
    
    # Top users by prediction count
    top_users = db.query(
        User.email,
        User.first_name,
        User.last_name,
        func.count(Prediction.id).label('prediction_count')
    )\
    .join(Prediction)\
    .group_by(User.id)\
    .order_by(desc('prediction_count'))\
    .limit(10)\
    .all()
    
    # Emotion distribution (system-wide)
    all_predictions = db.query(Prediction).all()
    emotion_counts = {}
    
    for pred in all_predictions:
        for face in pred.faces_data:
            emotion = face.get('emotion', 'Unknown')
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
    
    return {
        "recent_predictions": [
            {
                "id": p.id,
                "user_id": p.user_id,
                "num_faces": p.num_faces,
                "created_at": p.created_at
            }
            for p in recent_predictions
        ],
        "top_users": [
            {
                "email": email,
                "name": f"{first_name} {last_name}",
                "prediction_count": count
            }
            for email, first_name, last_name, count in top_users
        ],
        "emotion_distribution": emotion_counts
    }
