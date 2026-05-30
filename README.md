# AI-Based Image Analysis Tool
### Smile, Age & Emotion Prediction — Springboard Internship 2025 | Feb Batch-8 2026

A full-stack web application that analyzes facial images to predict age, detect smiles, recognize emotions, and recommend music based on mood.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, Axios, React Dropzone |
| Backend | FastAPI (Python 3.10) |
| Database | SQLite (SQLAlchemy ORM) |
| ML Models | TensorFlow/Keras, OpenCV DNN |
| Auth | JWT (python-jose + passlib/bcrypt) |
| PDF Reports | ReportLab |

---

## Features

- Multi-face detection using OpenCV DNN SSD (`res10_300x300_ssd_iter_140000`)
- Per-face age prediction (UTKFace-trained Keras model, MAE ~6.5 years)
- Smile detection — 3-signal ensemble (ML + cascade + geometry)
- Emotion recognition — 7 classes (Angry, Disgust, Fear, Happy, Sad, Surprise, Neutral) using FER2013 mini-XCEPTION model
- Music recommendations per emotion with Spotify links
- Batch image analysis
- Prediction history with image thumbnails
- Analytics dashboard (trends, age distribution, emotion breakdown)
- PDF report generation per prediction
- CSV export of history
- Admin panel
- Dark / Light theme toggle

---

## Project Structure

```
AI_Smile_Age_Prediction/
├── backend_fastapi/              # Active FastAPI backend
│   ├── app/
│   │   ├── main.py              # App entry point, middleware, routers
│   │   ├── config.py            # Settings (pydantic-settings)
│   │   ├── database.py          # SQLAlchemy setup
│   │   ├── models.py            # ORM models (User, Prediction, APILog)
│   │   ├── schemas.py           # Pydantic request/response schemas
│   │   ├── auth/                # JWT login, register, token refresh
│   │   ├── users/               # Profile CRUD
│   │   ├── prediction/          # Image analysis + ML service
│   │   │   ├── router.py        # Analyze, history, image serve, batch, CSV, insights
│   │   │   └── ml_service.py    # Face detection, age/smile/emotion models
│   │   ├── analytics/           # Summary, trends, age distribution
│   │   ├── reports/             # PDF generation (ReportLab)
│   │   ├── admin/               # Admin user/prediction management
│   │   └── models_mgmt/         # Model info endpoints
│   ├── ml_models/               # Trained model files
│   │   ├── age_model.keras
│   │   ├── emotion_model.hdf5   # FER2013 mini-XCEPTION (852KB)
│   │   ├── smile_model.h5
│   │   ├── deploy.prototxt      # SSD face detector config
│   │   ├── res10_300x300_ssd_iter_140000.caffemodel
│   │   └── haarcascade_frontalface_default.xml
│   ├── uploads/                 # Uploaded images (auto-created)
│   ├── reports/                 # Generated PDFs (auto-created)
│   ├── .env                     # Environment variables (see .env.example)
│   ├── .env.example
│   └── requirements.txt
│
├── frontend/                    # React frontend
│   ├── src/
│   │   ├── App.js               # Root, theme, auth state
│   │   ├── AuthPage.js          # Login / Register with password strength
│   │   ├── Dashboard.js         # 8-tab dashboard
│   │   └── index.css            # Design system (CSS variables, dark/light)
│   └── package.json
│
├── backend/                     # Legacy Flask backend (reference only)
└── README.md
```

---

## Setup & Running

### Prerequisites
- Python 3.10
- Node.js 18+
- npm

### 1. Backend

```bash
cd backend_fastapi

# Copy and configure environment
cp .env.example .env
# Edit .env — set SECRET_KEY, JWT_SECRET_KEY, DATABASE_URL

# Install dependencies
pip install -r requirements.txt

# Start server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Server runs at `http://localhost:8000`
Interactive API docs at `http://localhost:8000/docs`

### 2. Frontend

```bash
cd frontend
npm install
npm start
```

App runs at `http://localhost:3000`

---

## Environment Variables

Copy `backend_fastapi/.env.example` to `backend_fastapi/.env` and set:

```env
SECRET_KEY=your-secret-key-min-32-chars
JWT_SECRET_KEY=your-jwt-secret-min-32-chars
DATABASE_URL=sqlite:///./ai_image_analysis.db
CORS_ORIGINS=http://localhost:3000
```

---

## API Endpoints

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login, returns JWT |
| POST | `/api/auth/refresh` | Refresh access token |

### Prediction (JWT required)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/prediction/analyze` | Analyze single image |
| POST | `/api/prediction/batch-analyze` | Analyze multiple images |
| GET | `/api/prediction/history` | Get prediction history |
| GET | `/api/prediction/image/{id}` | Serve original uploaded image |
| GET | `/api/prediction/history/{id}` | Get prediction detail |
| DELETE | `/api/prediction/history/{id}` | Delete prediction |
| GET | `/api/prediction/export-csv` | Export history as CSV |
| GET | `/api/prediction/insights` | Get ML insights |

### Analytics (JWT required)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/analytics/summary` | Overall stats |
| GET | `/api/analytics/trends` | Daily trends |
| GET | `/api/analytics/age-distribution` | Age range breakdown |

### Reports (JWT required)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/reports/generate` | Generate PDF report (returns blob) |

### Users (JWT required)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/users/profile` | Get profile |
| PUT | `/api/users/profile` | Update profile |
| DELETE | `/api/users/profile` | Delete account |

### Admin (JWT + admin role required)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/admin/users` | List all users |
| DELETE | `/api/admin/users/{id}` | Delete user |
| GET | `/api/admin/predictions` | List all predictions |

---

## ML Models

| Model | File | Details |
|-------|------|---------|
| Face Detector | `res10_300x300_ssd_iter_140000.caffemodel` | OpenCV DNN SSD, confidence threshold 0.5 |
| Age | `age_model.keras` | CNN trained on UTKFace, MAE ~6.5 yrs |
| Smile | `smile_model.h5` | 3-signal ensemble + skin-tone invariance |
| Emotion | `emotion_model.hdf5` | FER2013 mini-XCEPTION, 7 classes |

### Emotion Labels (index order)
`Angry, Disgust, Fear, Happy, Sad, Surprise, Neutral`

### Music Recommendations
Each emotion maps to 5 curated tracks with Spotify links, returned in `faces[].music_recommendations` per analyzed face.

---

## Dashboard Tabs

1. Analyze — drag/drop or click to upload, view per-face results with music cards
2. Compare — side-by-side comparison of two images
3. History — paginated list with image thumbnails, PDF download, delete
4. Analytics — charts for trends, age distribution, emotion breakdown
5. Insights — ML model performance stats
6. Batch — analyze multiple images at once
7. Reports — generate and download PDF reports
8. Settings — theme toggle, account management

---

## Developer

**Manikanta** — Springboard Internship 2025, Feb Batch-8 2026
Branch: `Manikanta`
Repo: [Springboard-Internship-2025/AI-Based-Image-Analysis-Tool-for-Smile-and-Age-Prediction_Feb_Batch-8_2026](https://github.com/Springboard-Internship-2025/AI-Based-Image-Analysis-Tool-for-Smile-and-Age-Prediction_Feb_Batch-8_2026)
