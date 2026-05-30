"""
User management routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import User, Prediction
from ..schemas import UserResponse, UserUpdate
from ..auth.dependencies import get_current_user

router = APIRouter(prefix="/api/users", tags=["User Management"])


@router.get("/profile", response_model=UserResponse)
async def get_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile"""
    return current_user


@router.put("/profile", response_model=UserResponse)
async def update_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update user profile
    
    Only provided fields will be updated
    """
    if user_update.first_name:
        current_user.first_name = user_update.first_name
    if user_update.last_name:
        current_user.last_name = user_update.last_name
    if user_update.phone:
        current_user.phone = user_update.phone
    
    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/history/count")
async def get_upload_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's total upload count"""
    count = db.query(Prediction).filter(Prediction.user_id == current_user.id).count()
    return {"total_uploads": count}


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete user account
    
    This will also delete all associated predictions and reports
    """
    db.delete(current_user)
    db.commit()
    return None


@router.post("/change-password")
async def change_password(
    current_password: str,
    new_password: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change user password"""
    # Verify current password
    if not current_user.verify_password(current_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password"
        )
    
    # Validate new password
    if len(new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters"
        )
    
    # Update password
    current_user.hashed_password = User.get_password_hash(new_password)
    db.commit()
    
    return {"message": "Password changed successfully"}
