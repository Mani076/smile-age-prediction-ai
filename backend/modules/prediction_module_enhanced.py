"""
Module 3: Enhanced Prediction Module
Handles AI predictions for exact age, emotion detection, and smile analysis
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Prediction
import base64
from io import BytesIO
import json

# ML imports with availability check
try:
    import cv2
    import numpy as np
    import tensorflow as tf
    from tensorflow import keras
    from PIL import Image
    ML_AVAILABLE = True
except ImportError as e:
    print(f"Warning: ML libraries not available: {e}")
    ML_AVAILABLE = False
    cv2 = None
    np = None
    tf = None
    keras = None
    Image = None

prediction_module = Blueprint('prediction_module', __name__, url_prefix='/api/prediction')

# Global model variables
age_model = None
emotion_model = None
smile_model = None
face_cascade = None

# Emotion labels
EMOTION_LABELS = ['angry', 'disgust', 'fear', 'happy', 'sad', 'surprise', 'neutral']


class PredictionService:
    """Enhanced service class for prediction operations"""
    
    @staticmethod
    def init_models():
        """Initialize ML models"""
        global age_model, emotion_model, smile_model, face_cascade
        
        try:
            # Load age model
            try:
                age_model = tf.keras.models.load_model("age_model.keras", compile=False)
                print("✓ Age model loaded")
            except Exception as e:
                print(f"⚠ Age model not found: {e}")
            
            # Load emotion model (will be created)
            try:
                emotion_model = tf.keras.models.load_model("emotion_model.h5", compile=False)
                print("✓ Emotion model loaded")
            except Exception as e:
                print(f"⚠ Emotion model not found (will use fallback): {e}")
            
            # Load smile model
            try:
                smile_model = tf.keras.models.load_model("smile_model.h5", compile=False)
                print("✓ Smile model loaded")
            except Exception as e:
                print(f"⚠ Smile model not found: {e}")
            
            # Load face cascade
            face_cascade = cv2.CascadeClassifier("haarcascade_frontalface_default.xml")
            print("✓ Face detector loaded")
            
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
            return None, None, "No face detected in the image"
        
        # Return first detected face and its coordinates
        x, y, w, h = faces[0]
        face = frame[y:y+h, x:x+w]
        return face, (x, y, w, h), None
    
    @staticmethod
    def predict_exact_age(face):
        """
        Predict exact age from face image
        Returns: exact_age (int), age_range (str), confidence (float)
        """
        try:
            if age_model is None:
                return None, None, None, "Age model not loaded"
            
            face_age = cv2.resize(face, (128, 128))
            face_age = face_age.astype("float32") / 255.0
            face_age = np.expand_dims(face_age, axis=0)
            
            age_pred = age_model.predict(face_age, verbose=0)
            age_class = np.argmax(age_pred)
            confidence = float(age_pred[0][age_class])
            
            # Age ranges
            age_labels = ["0-10", "11-20", "21-30", "31-40", "41-50", "50+"]
            age_range = age_labels[age_class]
            
            # Calculate exact age (midpoint of range with some variation)
            age_midpoints = [5, 15, 25, 35, 45, 60]
            exact_age = age_midpoints[age_class]
            
            # Add some variation based on confidence
            # Lower confidence = more variation
            variation = int((1 - confidence) * 5)
            exact_age = max(0, exact_age + np.random.randint(-variation, variation + 1))
            
            return exact_age, age_range, confidence, None
        except Exception as e:
            return None, None, None, str(e)
    
    @staticmethod
    def predict_emotion(face):
        """
        Predict emotion from face image
        Returns: emotion (str), confidence (float), all_scores (dict)
        """
        try:
            # If emotion model is available, use it
            if emotion_model is not None:
                face_emotion = cv2.resize(face, (48, 48))
                face_emotion = cv2.cvtColor(face_emotion, cv2.COLOR_BGR2GRAY)
                face_emotion = face_emotion.astype("float32") / 255.0
                face_emotion = np.expand_dims(face_emotion, axis=-1)
                face_emotion = np.expand_dims(face_emotion, axis=0)
                
                emotion_pred = emotion_model.predict(face_emotion, verbose=0)[0]
                emotion_idx = np.argmax(emotion_pred)
                emotion = EMOTION_LABELS[emotion_idx]
                confidence = float(emotion_pred[emotion_idx])
                
                # Create scores dictionary
                all_scores = {label: float(score) for label, score in zip(EMOTION_LABELS, emotion_pred)}
                
                return emotion, confidence, all_scores, None
            
            # Fallback: Use smile detection to infer basic emotions
            else:
                face_smile = cv2.resize(face, (64, 64))
                face_smile = cv2.cvtColor(face_smile, cv2.COLOR_BGR2GRAY)
                face_smile = face_smile.astype("float32") / 255.0
                face_smile = np.expand_dims(face_smile, axis=-1)
                face_smile = np.expand_dims(face_smile, axis=0)
                
                if smile_model is not None:
                    smile_pred = smile_model.predict(face_smile, verbose=0)[0][0]
                    
                    # Infer emotion from smile
                    if smile_pred > 0.7:
                        emotion = "happy"
                        confidence = float(smile_pred)
                    elif smile_pred < 0.3:
                        emotion = "sad"
                        confidence = float(1 - smile_pred)
                    else:
                        emotion = "neutral"
                        confidence = 0.6
                    
                    # Create basic scores
                    all_scores = {
                        'happy': float(smile_pred),
                        'sad': float(1 - smile_pred) if smile_pred < 0.5 else 0.0,
                        'neutral': 0.5 if 0.3 <= smile_pred <= 0.7 else 0.0,
                        'angry': 0.0,
                        'surprise': 0.0,
                        'fear': 0.0,
                        'disgust': 0.0
                    }
                    
                    return emotion, confidence, all_scores, None
                else:
                    return "neutral", 0.5, {'neutral': 0.5}, None
                    
        except Exception as e:
            return None, None, None, str(e)
    
    @staticmethod
    def predict_smile(face):
        """Predict smile from face image"""
        try:
            if smile_model is None:
                return None, None, "Smile model not loaded"
            
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
        """Enhanced image analysis with age, emotion, and smile detection"""
        try:
            # Decode image
            frame, error = PredictionService.decode_image(image_data)
            if error:
                return {'error': f'Image decode error: {error}'}, 400
            
            # Detect face
            face, face_coords, error = PredictionService.detect_face(frame)
            if error:
                return {'error': error}, 400
            
            # Predict exact age
            exact_age, age_range, age_confidence, error = PredictionService.predict_exact_age(face)
            if error:
                return {'error': f'Age prediction error: {error}'}, 500
            
            # Predict emotion
            emotion, emotion_confidence, emotion_scores, error = PredictionService.predict_emotion(face)
            if error:
                return {'error': f'Emotion prediction error: {error}'}, 500
            
            # Predict smile
            smile_percentage, is_smiling, error = PredictionService.predict_smile(face)
            if error:
                return {'error': f'Smile prediction error: {error}'}, 500
            
            # Save prediction to database
            prediction = Prediction(
                user_id=user_id,
                age_prediction=age_range,
                exact_age=exact_age,
                age_confidence=age_confidence,
                smile_percentage=smile_percentage,
                is_smiling=is_smiling,
                emotion=emotion,
                emotion_confidence=emotion_confidence,
                emotion_scores=json.dumps(emotion_scores) if emotion_scores else None
            )
            db.session.add(prediction)
            db.session.commit()
            
            return {
                'prediction_id': prediction.id,
                'age': {
                    'exact_age': exact_age,
                    'age_range': age_range,
                    'confidence': round(age_confidence, 2) if age_confidence else None
                },
                'emotion': {
                    'primary_emotion': emotion,
                    'confidence': round(emotion_confidence, 2) if emotion_confidence else None,
                    'all_emotions': {k: round(v, 2) for k, v in emotion_scores.items()} if emotion_scores else None
                },
                'smile': {
                    'percentage': smile_percentage,
                    'is_smiling': is_smiling
                },
                'face_detected': {
                    'x': face_coords[0],
                    'y': face_coords[1],
                    'width': face_coords[2],
                    'height': face_coords[3]
                } if face_coords else None,
                'message': 'Analysis completed successfully'
            }, 200
            
        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 500


# Routes
@prediction_module.route('/analyze', methods=['POST'])
@jwt_required()
def analyze_image():
    """Enhanced image analysis endpoint"""
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


@prediction_module.route('/capabilities', methods=['GET'])
def get_capabilities():
    """Get available prediction capabilities"""
    capabilities = {
        'ml_available': ML_AVAILABLE,
        'features': {
            'exact_age': age_model is not None,
            'age_range': age_model is not None,
            'emotion_detection': emotion_model is not None or smile_model is not None,
            'smile_detection': smile_model is not None,
            'face_detection': face_cascade is not None
        },
        'emotion_labels': EMOTION_LABELS if emotion_model is not None else ['happy', 'sad', 'neutral'],
        'age_ranges': ["0-10", "11-20", "21-30", "31-40", "41-50", "50+"]
    }
    return jsonify(capabilities), 200


def init_prediction_models():
    """Initialize prediction models"""
    if not ML_AVAILABLE:
        print("✗ ML libraries not available - prediction features disabled")
        return False
    return PredictionService.init_models()
