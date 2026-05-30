"""
Authentication dependencies and utilities
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional

from ..database import get_db
from ..models import User
from ..schemas import TokenData
from ..config import get_settings

settings = get_settings()

# Security scheme for Swagger
security = HTTPBearer()


# ---------------------------------------------------
# Create Access Token
# ---------------------------------------------------
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""

    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update(
        {
            "exp": expire,
            "type": "access"
        }
    )

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )

    return encoded_jwt


# ---------------------------------------------------
# Create Refresh Token
# ---------------------------------------------------
def create_refresh_token(data: dict) -> str:
    """Create JWT refresh token"""

    to_encode = data.copy()

    expire = datetime.utcnow() + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )

    to_encode.update(
        {
            "exp": expire,
            "type": "refresh"
        }
    )

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )

    return encoded_jwt


# ---------------------------------------------------
# Verify Token
# ---------------------------------------------------
def verify_token(token: str) -> TokenData:
    """Verify and decode JWT token"""

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )

        user_id = payload.get("sub")
        email = payload.get("email")
        role = payload.get("role")

        if user_id is None:
            raise credentials_exception

        token_data = TokenData(
            user_id=int(user_id),
            email=email,
            role=role
        )

        return token_data

    except JWTError:
        raise credentials_exception


# ---------------------------------------------------
# Get Current User
# ---------------------------------------------------
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user"""

    token = credentials.credentials

    token_data = verify_token(token)

    user = db.query(User).filter(User.id == token_data.user_id).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )

    return user


# ---------------------------------------------------
# Admin Check
# ---------------------------------------------------
async def get_current_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """Verify current user is admin"""

    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    return current_user