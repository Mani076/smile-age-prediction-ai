"""
Main FastAPI application
"""
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import time
import logging

from .config import get_settings
from .database import init_db, get_db
from .models import APILog

# Import routers
from .auth.router import router as auth_router
from .users.router import router as users_router
from .prediction.router import router as prediction_router
from .analytics.router import router as analytics_router
from .reports.router import router as reports_router
from .admin.router import router as admin_router
from .models_mgmt.router import router as models_router

# Import ML service for initialization
from .prediction.ml_service import ml_service

settings = get_settings()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("Starting AI Image Analysis API...")
    
    # Initialize database
    init_db()
    logger.info("Database initialized")
    
    # Load ML models
    logger.info("Loading ML models...")
    if ml_service.load_models():
        logger.info("ML models loaded successfully")
    else:
        logger.warning("ML models not loaded - predictions may use fallback values")
    
    yield
    
    # Shutdown
    logger.info("Shutting down API...")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    ## AI-Based Image Analysis Tool
    
    Production-ready API for smile, age, and emotion prediction from images.
    
    ### Features:
    - 🔐 JWT Authentication
    - 👤 User Management
    - 🤖 Multi-face AI Predictions (Age, Smile, Emotion)
    - 📊 Analytics & Insights
    - 📄 PDF Report Generation
    - 🔧 Model Management
    - 👨‍💼 Admin Dashboard
    
    ### Tech Stack:
    - FastAPI
    - PostgreSQL
    - TensorFlow/Keras
    - OpenCV
    - JWT Authentication
    """,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all API requests"""
    start_time = time.time()
    
    # Process request
    response = await call_next(request)
    
    # Calculate response time
    process_time = (time.time() - start_time) * 1000  # milliseconds
    
    # Log to database (async in production)
    try:
        # Get user_id from token if available
        user_id = None
        auth_header = request.headers.get("Authorization")
        if auth_header:
            # Extract user_id from token (simplified)
            pass
        
        # Note: In production, use background tasks for logging
        # to avoid blocking the response
        logger.info(
            f"{request.method} {request.url.path} - "
            f"Status: {response.status_code} - "
            f"Time: {process_time:.2f}ms"
        )
    except Exception as e:
        logger.error(f"Error logging request: {e}")
    
    # Add custom headers
    response.headers["X-Process-Time"] = str(process_time)
    
    return response


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": exc.errors(),
            "message": "Validation error"
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "message": "Internal server error",
            "detail": str(exc) if settings.DEBUG else "An error occurred"
        }
    )


# Register routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(prediction_router)
app.include_router(analytics_router)
app.include_router(reports_router)
app.include_router(admin_router)
app.include_router(models_router)


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """API root endpoint with HTML response"""
    from fastapi.responses import HTMLResponse
    
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AI Image Analysis API</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                margin: 0;
                padding: 20px;
            }
            .container {
                background: white;
                border-radius: 20px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                padding: 50px;
                max-width: 800px;
                width: 100%;
            }
            h1 {
                color: #667eea;
                margin-bottom: 10px;
                font-size: 36px;
            }
            .subtitle {
                color: #666;
                margin-bottom: 30px;
                font-size: 18px;
            }
            .status {
                background: #d4edda;
                border: 2px solid #c3e6cb;
                color: #155724;
                padding: 20px;
                border-radius: 10px;
                margin-bottom: 30px;
                text-align: center;
            }
            .buttons {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 15px;
                margin-bottom: 30px;
            }
            .btn {
                padding: 15px 30px;
                border-radius: 10px;
                text-decoration: none;
                font-weight: 600;
                font-size: 16px;
                text-align: center;
                transition: transform 0.2s;
                display: block;
            }
            .btn:hover {
                transform: translateY(-2px);
            }
            .btn-primary {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }
            .btn-secondary {
                background: #f8f9fa;
                color: #667eea;
                border: 2px solid #667eea;
            }
            .info-box {
                background: #f8f9fa;
                padding: 20px;
                border-radius: 10px;
                margin-bottom: 20px;
            }
            .info-box h3 {
                color: #667eea;
                margin-bottom: 15px;
            }
            .info-box ul {
                list-style: none;
                padding: 0;
            }
            .info-box li {
                padding: 8px 0;
                border-bottom: 1px solid #e0e0e0;
            }
            .info-box li:last-child {
                border-bottom: none;
            }
            .footer {
                text-align: center;
                color: #666;
                font-size: 14px;
                margin-top: 30px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 AI Image Analysis API</h1>
            <p class="subtitle">FastAPI Backend - Version 1.0.0</p>
            
            <div class="status">
                <h2>✅ Server is Running</h2>
                <p>FastAPI backend is active on port 8000</p>
            </div>
            
            <div class="buttons">
                <a href="/docs" class="btn btn-primary">📚 Interactive API Docs</a>
                <a href="/redoc" class="btn btn-primary">📖 Alternative Docs</a>
                <a href="/health" class="btn btn-secondary">🏥 Health Check</a>
                <a href="/api/info" class="btn btn-secondary">ℹ️ API Info</a>
            </div>
            
            <div class="info-box">
                <h3>🚀 Features</h3>
                <ul>
                    <li>✅ User Authentication (JWT)</li>
                    <li>✅ Multi-face Detection</li>
                    <li>✅ Age Prediction</li>
                    <li>✅ Smile Detection</li>
                    <li>✅ Emotion Recognition (7 emotions)</li>
                    <li>✅ Analytics Dashboard</li>
                    <li>✅ PDF Report Generation</li>
                    <li>✅ Model Management</li>
                    <li>✅ Admin Panel</li>
                </ul>
            </div>
            
            <div class="info-box">
                <h3>📡 Quick Links</h3>
                <ul>
                    <li><a href="/docs" style="color: #667eea;">Interactive API Documentation (Swagger UI)</a></li>
                    <li><a href="/redoc" style="color: #667eea;">Alternative Documentation (ReDoc)</a></li>
                    <li><a href="/health" style="color: #667eea;">Health Check Endpoint</a></li>
                    <li><a href="/api/info" style="color: #667eea;">API Information</a></li>
                </ul>
            </div>
            
            <div class="footer">
                <p><strong>Base URL:</strong> http://localhost:8000</p>
                <p>AI-Based Image Analysis Tool for Smile and Age Prediction</p>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


# Health check
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "models_loaded": ml_service.models_loaded
    }


# API info
@app.get("/api/info", tags=["Info"])
async def api_info():
    """Get API information"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "features": [
            "User Authentication (JWT)",
            "Multi-face Detection",
            "Age Prediction",
            "Smile Detection",
            "Emotion Recognition",
            "Analytics Dashboard",
            "PDF Report Generation",
            "Model Management",
            "Admin Panel"
        ],
        "supported_emotions": [
            "Happy", "Sad", "Angry", "Neutral", 
            "Fear", "Surprise", "Disgust"
        ],
        "max_upload_size_mb": settings.MAX_UPLOAD_SIZE / (1024 * 1024),
        "allowed_formats": list(settings.allowed_extensions_set)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
