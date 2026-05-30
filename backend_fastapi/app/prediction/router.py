"""
Prediction routes for AI analysis
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session
from pathlib import Path
import shutil
from typing import List
import uuid
import csv
import io

from ..database import get_db
from ..models import User, Prediction
from ..schemas import PredictionResponse, PredictionHistory
from ..auth.dependencies import get_current_user
from ..config import get_settings
from .ml_service import ml_service

settings = get_settings()
router = APIRouter(prefix="/api/prediction", tags=["AI Prediction"])

# Ensure upload directory exists
UPLOAD_DIR = Path(settings.UPLOAD_DIR)
UPLOAD_DIR.mkdir(exist_ok=True)


def validate_image(file: UploadFile) -> None:
    """Validate uploaded image file"""
    # Check content type first (webcam captures may have no extension)
    if file.content_type and file.content_type.startswith('image/'):
        return  # content type is valid, skip extension check

    # Fall back to extension check
    file_ext = Path(file.filename or "").suffix.lower()
    if file_ext and file_ext not in settings.allowed_extensions_set:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(settings.allowed_extensions_set)}"
        )


@router.post("/analyze")
async def analyze_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload and analyze image for age, smile, and emotion detection
    
    Supports multi-face detection
    
    - **file**: Image file (JPG, PNG, WEBP)
    
    Returns predictions for all detected faces
    """
    # Validate file
    validate_image(file)
    
    # Save uploaded file
    file_id = str(uuid.uuid4())
    file_ext = Path(file.filename or "webcam.jpg").suffix or ".jpg"
    file_path = UPLOAD_DIR / f"{file_id}{file_ext}"
    
    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )
    
    # Analyze image
    try:
        results = ml_service.analyze_image(str(file_path))
    except Exception as e:
        # Clean up file on error
        file_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )
    
    # Calculate aggregated data
    num_faces = results["num_faces"]
    avg_age = None
    smile_count = 0
    dominant_emotion = None
    
    if num_faces > 0:
        # Filter out None ages (models not trained yet)
        ages = [face["age"] for face in results["faces"] if face["age"] is not None]
        avg_age = sum(ages) / len(ages) if ages else None
        smile_count = sum(1 for face in results["faces"] if face.get("smile"))

        # Find most common emotion, ignoring Unknown
        emotions = [face["emotion"] for face in results["faces"] if face.get("emotion") and face["emotion"] != "Unknown"]
        dominant_emotion = max(set(emotions), key=emotions.count) if emotions else None
    
    # Save to database
    prediction = Prediction(
        user_id=current_user.id,
        image_path=str(file_path),
        faces_data=results["faces"],
        num_faces=num_faces,
        avg_age=avg_age,
        smile_count=smile_count,
        dominant_emotion=dominant_emotion,
        model_version=results["model_version"],
        processing_time=results["processing_time"]
    )
    
    db.add(prediction)
    db.commit()
    db.refresh(prediction)
    
    # Return response
    return {
        "prediction_id": prediction.id,
        "num_faces": num_faces,
        "faces": results["faces"],
        "processing_time": results["processing_time"],
        "model_version": results["model_version"],
        "models_trained": results.get("models_trained", False),
        "created_at": prediction.created_at
    }


@router.get("/history")
async def get_prediction_history(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    predictions = db.query(Prediction)\
        .filter(Prediction.user_id == current_user.id)\
        .order_by(Prediction.created_at.desc())\
        .offset(skip)\
        .limit(limit)\
        .all()

    # Attach image_url so frontend can show thumbnails
    result = []
    for p in predictions:
        d = {
            "id": p.id,
            "num_faces": p.num_faces,
            "avg_age": p.avg_age,
            "smile_count": p.smile_count,
            "dominant_emotion": p.dominant_emotion,
            "model_version": p.model_version,
            "processing_time": p.processing_time,
            "created_at": p.created_at,
            "faces_data": p.faces_data,
            "image_url": f"/api/prediction/image/{p.id}",
        }
        result.append(d)
    return result


@router.get("/image/{prediction_id}")
async def get_prediction_image(
    prediction_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Serve the original uploaded image for a prediction."""
    prediction = db.query(Prediction)\
        .filter(
            Prediction.id == prediction_id,
            Prediction.user_id == current_user.id
        ).first()

    if not prediction:
        raise HTTPException(status_code=404, detail="Prediction not found")

    image_path = Path(prediction.image_path)
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Image file not found")

    # Detect media type from extension
    ext = image_path.suffix.lower()
    media_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    media_type = media_map.get(ext, "image/jpeg")

    return FileResponse(str(image_path), media_type=media_type)


@router.get("/history/{prediction_id}", response_model=PredictionResponse)
async def get_prediction_detail(
    prediction_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed prediction result by ID"""
    prediction = db.query(Prediction)\
        .filter(
            Prediction.id == prediction_id,
            Prediction.user_id == current_user.id
        )\
        .first()
    
    if not prediction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prediction not found"
        )
    
    return {
        "prediction_id": prediction.id,
        "num_faces": prediction.num_faces,
        "faces": prediction.faces_data,
        "processing_time": prediction.processing_time,
        "model_version": prediction.model_version,
        "created_at": prediction.created_at
    }


@router.delete("/history/{prediction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prediction(
    prediction_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a prediction and its associated image"""
    prediction = db.query(Prediction)\
        .filter(
            Prediction.id == prediction_id,
            Prediction.user_id == current_user.id
        )\
        .first()
    
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


@router.post("/batch-analyze")
async def batch_analyze(
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Analyze multiple images at once (max 10)."""
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 images per batch")

    results = []
    for file in files:
        validate_image(file)
        file_id = str(uuid.uuid4())
        file_ext = Path(file.filename or "upload.jpg").suffix or ".jpg"
        file_path = UPLOAD_DIR / f"{file_id}{file_ext}"
        try:
            with file_path.open("wb") as buf:
                shutil.copyfileobj(file.file, buf)
            analysis = ml_service.analyze_image(str(file_path))
            num_faces = analysis["num_faces"]
            ages = [f["age"] for f in analysis["faces"] if f["age"] is not None]
            avg_age = sum(ages) / len(ages) if ages else None
            smile_count = sum(1 for f in analysis["faces"] if f.get("smile"))
            emotions = [f["emotion"] for f in analysis["faces"] if f.get("emotion") and f["emotion"] != "Unknown"]
            dominant_emotion = max(set(emotions), key=emotions.count) if emotions else None

            pred = Prediction(
                user_id=current_user.id,
                image_path=str(file_path),
                faces_data=analysis["faces"],
                num_faces=num_faces,
                avg_age=avg_age,
                smile_count=smile_count,
                dominant_emotion=dominant_emotion,
                model_version=analysis["model_version"],
                processing_time=analysis["processing_time"],
            )
            db.add(pred)
            db.commit()
            db.refresh(pred)
            results.append({
                "filename": file.filename,
                "prediction_id": pred.id,
                "num_faces": num_faces,
                "faces": analysis["faces"],
                "processing_time": analysis["processing_time"],
            })
        except Exception as e:
            results.append({"filename": file.filename, "error": str(e)})

    return {"batch_results": results, "total": len(results)}


@router.get("/export-csv")
async def export_history_csv(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export prediction history as CSV download."""
    predictions = (
        db.query(Prediction)
        .filter(Prediction.user_id == current_user.id)
        .order_by(Prediction.created_at.desc())
        .limit(1000)
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Date", "Faces", "Avg Age", "Smile Count",
        "Dominant Emotion", "Processing Time (s)", "Model Version"
    ])
    for p in predictions:
        writer.writerow([
            p.id,
            p.created_at.strftime("%Y-%m-%d %H:%M") if p.created_at else "",
            p.num_faces,
            round(p.avg_age, 1) if p.avg_age else "",
            p.smile_count,
            p.dominant_emotion or "",
            p.processing_time or "",
            p.model_version or "",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=analysis_history.csv"},
    )


@router.get("/insights")
async def get_insights(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate smart AI insights from user's prediction history."""
    predictions = (
        db.query(Prediction)
        .filter(Prediction.user_id == current_user.id)
        .order_by(Prediction.created_at.desc())
        .limit(50)
        .all()
    )

    if not predictions:
        return {"insights": [], "summary": "No analyses yet. Upload your first image to get insights!"}

    total = len(predictions)
    all_faces = [f for p in predictions for f in (p.faces_data or [])]
    ages = [f["age"] for f in all_faces if f.get("age")]
    smiles = [f for f in all_faces if f.get("smile")]
    emotions = [f.get("emotion", "").lower() for f in all_faces if f.get("emotion")]

    insights = []

    # Age insight
    if ages:
        avg_age = sum(ages) / len(ages)
        insights.append({
            "icon": "🎂",
            "title": "Age Profile",
            "text": f"Average detected age is {avg_age:.0f} years across {len(ages)} faces.",
            "color": "#f59e0b"
        })

    # Smile insight
    if all_faces:
        smile_rate = len(smiles) / len(all_faces) * 100
        mood = "very happy" if smile_rate > 70 else "mostly happy" if smile_rate > 40 else "often serious"
        insights.append({
            "icon": "😊",
            "title": "Smile Frequency",
            "text": f"{smile_rate:.0f}% of detected faces are smiling — you look {mood}!",
            "color": "#10b981"
        })

    # Emotion insight
    if emotions:
        from collections import Counter
        top = Counter(emotions).most_common(1)[0]
        insights.append({
            "icon": "🎭",
            "title": "Dominant Emotion",
            "text": f"'{top[0].capitalize()}' is your most frequent emotion ({top[1]} times).",
            "color": "#6366f1"
        })

    # Activity insight
    if total >= 5:
        insights.append({
            "icon": "📈",
            "title": "Activity",
            "text": f"You've run {total} analyses. Keep exploring your expressions!",
            "color": "#06b6d4"
        })

    # Multi-face insight
    multi = [p for p in predictions if p.num_faces > 1]
    if multi:
        insights.append({
            "icon": "👥",
            "title": "Group Photos",
            "text": f"{len(multi)} of your analyses contained multiple faces.",
            "color": "#8b5cf6"
        })

    return {"insights": insights, "total_faces_analyzed": len(all_faces)}
