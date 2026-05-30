from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Prediction, User
import cv2
import numpy as np
import tensorflow as tf
import base64
from io import BytesIO
from PIL import Image

prediction_bp = Blueprint('prediction', __name__, url_prefix='/api/prediction')

# Load models (will be initialized in app.py)
age_model = None
smile_model = None
face_cascade = None

def init_models():
    """Initialize ML models"""
    global age_model, smile_model, face_cascade
    
    try:
        age_model = tf.keras.models.load_model("age_model.keras", compile=False)
        smile_model = tf.keras.models.load_model("smile_model.h5", compile=False)
        face_cascade = cv2.CascadeClassifier("haarcascade_frontalface_default.xml")
        print("Models loaded successfully")
    except Exception as e:
        print(f"Error loading models: {e}")

@prediction_bp.route('/analyze', methods=['POST'])
@jwt_required()
def analyze_image():
    """Analyze image for age and smile detection"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        if 'image' not in data:
            return jsonify({'error': 'Image data is required'}), 400
        
        # Decode base64 image
        image_data = data['image'].split(',')[1] if ',' in data['image'] else data['image']
        image_bytes = base64.b64decode(image_data)
        image = Image.open(BytesIO(image_bytes))
        frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # Detect face
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        
        if len(faces) == 0:
            return jsonify({'error': 'No face detected in the image'}), 400
        
        # Process first detected face
        x, y, w, h = faces[0]
        face = frame[y:y+h, x:x+w]
        
        # Age prediction
        face_age = cv2.resize(face, (128, 128))
        face_age = face_age.astype("float32") / 255.0
        face_age = np.expand_dims(face_age, axis=0)
        age_pred = age_model.predict(face_age, verbose=0)
        age_class = np.argmax(age_pred)
        age_labels = ["0-10", "11-20", "21-30", "31-40", "41-50", "50+"]
        age_text = age_labels[age_class]
        
        # Smile prediction
        face_smile = cv2.resize(face, (64, 64))
        face_smile = cv2.cvtColor(face_smile, cv2.COLOR_BGR2GRAY)
        face_smile = face_smile.astype("float32") / 255.0
        face_smile = np.expand_dims(face_smile, axis=-1)
        face_smile = np.expand_dims(face_smile, axis=0)
        smile_pred = smile_model.predict(face_smile, verbose=0)[0][0]
        smile_percentage = int(smile_pred * 100)
        is_smiling = smile_percentage > 60
        
        # Save prediction to database
        prediction = Prediction(
            user_id=user_id,
            age_prediction=age_text,
            smile_percentage=smile_percentage,
            is_smiling=is_smiling
        )
        db.session.add(prediction)
        db.session.commit()
        
        return jsonify({
            'prediction': prediction.to_dict(),
            'age': age_text,
            'smile_percentage': smile_percentage,
            'is_smiling': is_smiling
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@prediction_bp.route('/history', methods=['GET'])
@jwt_required()
def get_history():
    """Get user's prediction history"""
    try:
        user_id = get_jwt_identity()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        predictions = Prediction.query.filter_by(user_id=user_id)\
            .order_by(Prediction.created_at.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'predictions': [p.to_dict() for p in predictions.items],
            'total': predictions.total,
            'pages': predictions.pages,
            'current_page': page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@prediction_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_stats():
    """Get user's prediction statistics"""
    try:
        user_id = get_jwt_identity()
        
        total_predictions = Prediction.query.filter_by(user_id=user_id).count()
        smiling_count = Prediction.query.filter_by(user_id=user_id, is_smiling=True).count()
        
        avg_smile = db.session.query(db.func.avg(Prediction.smile_percentage))\
            .filter_by(user_id=user_id).scalar() or 0
        
        return jsonify({
            'total_predictions': total_predictions,
            'smiling_count': smiling_count,
            'average_smile_percentage': round(avg_smile, 2)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
