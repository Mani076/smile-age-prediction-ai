"""
Module 3: Prediction Module
Handles AI predictions for age and smile detection
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Prediction
import base64
from io import BytesIO

# Temporarily disable ML imports for testing
try:
    import cv2
    import numpy as np
    import tensorflow as tf
    from PIL import Image
    ML_AVAILABLE = True
except ImportError as e:
    print(f"Warning: ML libraries not available: {e}")
    ML_AVAILABLE = False
    cv2 = None
    np = None
    tf = None
    Image = None

prediction_module = Blueprint('prediction_module', __name__, url_prefix='/api/prediction')

# Global model variables
age_model = None
smile_model = None
face_cascade = None


class PredictionService:
    """Service class for prediction operations"""
    
    @staticmethod
    def init_models():
        """Initialize ML models"""
        global age_model, smile_model, face_cascade
        
        try:
            age_model = tf.keras.models.load_model("age_model.keras", compile=False)
            smile_model = tf.keras.models.load_model("smile_model.h5", compile=False)
            face_cascade = cv2.CascadeClassifier("haarcascade_frontalface_default.xml")
            print("✓ ML Models loaded successfully")
            return True
        except Exception as e:
            print(f"✗ Error loading models: {e}")
            return False
    
    @staticmethod
    def decode_image(image_data):
        """Decode base64 image to numpy array"""
        try:
            # Remove data URI prefix if present
            if ',' in image_data:
                image_data = image_data.split(',')[1]
            
            # Decode base64
            image_bytes = base64.b64decode(image_data)
            image = Image.open(BytesIO(image_bytes))
            frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            return frame, None
        except Exception as e:
            return None, str(e)
    
    @staticmethod
    def detect_face(frame):
        """Detect face in image"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        
        if len(faces) == 0:
            return None, "No face detected in the image"
        
        # Return first detected face
        x, y, w, h = faces[0]
        face = frame[y:y+h, x:x+w]
        return face, None
    
    @staticmethod
    def predict_age(face):
        """Predict age from face image"""
        try:
            face_age = cv2.resize(face, (128, 128))
            face_age = face_age.astype("float32") / 255.0
            face_age = np.expand_dims(face_age, axis=0)
            
            age_pred = age_model.predict(face_age, verbose=0)
            age_class = np.argmax(age_pred)
            
            age_labels = ["0-10", "11-20", "21-30", "31-40", "41-50", "50+"]
            age_text = age_labels[age_class]
            confidence = float(age_pred[0][age_class])
            
            return age_text, confidence, None
        except Exception as e:
            return None, None, str(e)
    
    @staticmethod
    def predict_smile(face):
        """Predict smile from face image"""
        try:
            face_smile = cv2.resize(face, (64, 64))
            face_smile = cv2.cvtColor(face_smile, cv2.COLOR_BGR2GRAY)
            face_smile = face_smile.astype("float32") / 255.0
            face_smile = np.expand_dims(face_smile, axis=-1)
            face_smile = np.expand_dims(face_smile, axis=0)
            
            smile_pred = smile_model.predict(face_smile, verbose=0)[0][0]
            smile_percentage = int(smile_pred * 100)
            is_smiling = smile_percentage > 60
            
            return smile_percentage, is_smiling, None
        except Exception as e:
            return None, None, str(e)
    
    @staticmethod
    def analyze_image(user_id, image_data):
        """Analyze image for age and smile detection"""
        try:
            # Decode image
            frame, error = PredictionService.decode_image(image_data)
            if error:
                return {'error': f'Image decode error: {error}'}, 400
            
            # Detect face
            face, error = PredictionService.detect_face(frame)
            if error:
                return {'error': error}, 400
            
            # Predict age
            age_text, age_confidence, error = PredictionService.predict_age(face)
            if error:
                return {'error': f'Age prediction error: {error}'}, 500
            
            # Predict smile
            smile_percentage, is_smiling, error = PredictionService.predict_smile(face)
            if error:
                return {'error': f'Smile prediction error: {error}'}, 500
            
            # Save prediction to database
            prediction = Prediction(
                user_id=user_id,
                age_prediction=age_text,
                smile_percentage=smile_percentage,
                is_smiling=is_smiling
            )
            db.session.add(prediction)
            db.session.commit()
            
            return {
                'prediction': prediction.to_dict(),
                'age': age_text,
                'age_confidence': round(age_confidence, 2),
                'smile_percentage': smile_percentage,
                'is_smiling': is_smiling,
                'message': 'Analysis completed successfully'
            }, 200
            
        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 500


# Routes
@prediction_module.route('/analyze', methods=['POST'])
@jwt_required()
def analyze_image():
    """Analyze image for age and smile detection"""
    if not ML_AVAILABLE:
        return jsonify({
            'error': 'ML features are currently unavailable',
            'message': 'Please install required ML libraries: opencv-python, tensorflow, keras'
        }), 503
    
    user_id = get_jwt_identity()
    data = request.get_json()
    
    if 'image' not in data:
        return jsonify({'error': 'Image data is required'}), 400
    
    result, status_code = PredictionService.analyze_image(user_id, data['image'])
    return jsonify(result), status_code


def init_prediction_models():
    """Initialize prediction models"""
    if not ML_AVAILABLE:
        print("✗ ML libraries not available - prediction features disabled")
        return False
    return PredictionService.init_models()
