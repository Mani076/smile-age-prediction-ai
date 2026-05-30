"""
Model management routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import Model
from ..schemas import ModelResponse, ModelMetrics
from ..auth.dependencies import get_current_admin

router = APIRouter(prefix="/api/models", tags=["Model Management"])


@router.get("/list", response_model=List[ModelResponse])
async def list_models(
    db: Session = Depends(get_db)
):
    """Get list of all available models"""
    models = db.query(Model).order_by(Model.created_at.desc()).all()
    return models


@router.get("/active")
async def get_active_models(
    db: Session = Depends(get_db)
):
    """Get currently active models"""
    active_models = db.query(Model).filter(Model.is_active == True).all()
    
    result = {
        "age_model": None,
        "smile_model": None,
        "emotion_model": None
    }
    
    for model in active_models:
        if model.model_type == "age":
            result["age_model"] = {
                "version": model.version,
                "accuracy": model.accuracy,
                "file_path": model.file_path
            }
        elif model.model_type == "smile":
            result["smile_model"] = {
                "version": model.version,
                "accuracy": model.accuracy,
                "file_path": model.file_path
            }
        elif model.model_type == "emotion":
            result["emotion_model"] = {
                "version": model.version,
                "accuracy": model.accuracy,
                "file_path": model.file_path
            }
    
    return result


@router.post("/register", response_model=ModelResponse)
async def register_model(
    version: str,
    model_type: str,
    file_path: str,
    metrics: ModelMetrics = None,
    description: str = None,
    current_admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Register a new model version
    
    Admin only
    
    - **version**: Model version (e.g., "v1", "v2")
    - **model_type**: Type of model (age, smile, emotion)
    - **file_path**: Path to model file
    - **metrics**: Optional performance metrics
    - **description**: Optional description
    """
    # Check if version already exists
    existing = db.query(Model).filter(
        Model.version == version,
        Model.model_type == model_type
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model {model_type} version {version} already exists"
        )
    
    # Create new model
    new_model = Model(
        version=version,
        model_type=model_type,
        file_path=file_path,
        description=description,
        is_active=False
    )
    
    if metrics:
        new_model.accuracy = metrics.accuracy
        new_model.precision = metrics.precision
        new_model.recall = metrics.recall
        new_model.f1_score = metrics.f1_score
    
    db.add(new_model)
    db.commit()
    db.refresh(new_model)
    
    return new_model


@router.put("/{model_id}/activate")
async def activate_model(
    model_id: int,
    current_admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Activate a model version
    
    Deactivates other models of the same type
    
    Admin only
    """
    model = db.query(Model).filter(Model.id == model_id).first()
    
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )
    
    # Deactivate other models of same type
    db.query(Model)\
        .filter(Model.model_type == model.model_type)\
        .update({"is_active": False})
    
    # Activate this model
    model.is_active = True
    db.commit()
    
    return {
        "message": f"Model {model.version} ({model.model_type}) activated",
        "model_id": model.id,
        "version": model.version
    }


@router.put("/{model_id}/metrics")
async def update_model_metrics(
    model_id: int,
    metrics: ModelMetrics,
    current_admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Update model performance metrics
    
    Admin only
    """
    model = db.query(Model).filter(Model.id == model_id).first()
    
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )
    
    if metrics.accuracy is not None:
        model.accuracy = metrics.accuracy
    if metrics.precision is not None:
        model.precision = metrics.precision
    if metrics.recall is not None:
        model.recall = metrics.recall
    if metrics.f1_score is not None:
        model.f1_score = metrics.f1_score
    
    db.commit()
    db.refresh(model)
    
    return model


@router.get("/{model_id}/performance")
async def get_model_performance(
    model_id: int,
    db: Session = Depends(get_db)
):
    """Get detailed model performance metrics"""
    model = db.query(Model).filter(Model.id == model_id).first()
    
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )
    
    return {
        "model_id": model.id,
        "version": model.version,
        "model_type": model.model_type,
        "is_active": model.is_active,
        "metrics": {
            "accuracy": model.accuracy,
            "precision": model.precision,
            "recall": model.recall,
            "f1_score": model.f1_score
        },
        "description": model.description,
        "created_at": model.created_at
    }


@router.delete("/{model_id}")
async def delete_model(
    model_id: int,
    current_admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Delete a model
    
    Cannot delete active models
    
    Admin only
    """
    model = db.query(Model).filter(Model.id == model_id).first()
    
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )
    
    if model.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete active model. Activate another model first."
        )
    
    db.delete(model)
    db.commit()
    
    return {"message": "Model deleted successfully"}
