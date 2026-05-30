from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    """User model for authentication and profile management"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone_number = db.Column(db.String(15), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    predictions = db.relationship('Prediction', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verify password"""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        """Convert user object to dictionary"""
        return {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'email': self.email,
            'phone_number': self.phone_number,
            'created_at': self.created_at.isoformat(),
            'is_active': self.is_active
        }

class Prediction(db.Model):
    """Model to store prediction history"""
    __tablename__ = 'predictions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Age predictions
    age_prediction = db.Column(db.String(20), nullable=False)  # Age range (backward compatibility)
    exact_age = db.Column(db.Integer, nullable=True)  # NEW: Exact age prediction
    age_confidence = db.Column(db.Float, nullable=True)  # NEW: Confidence score
    
    # Smile predictions
    smile_percentage = db.Column(db.Integer, nullable=False)
    is_smiling = db.Column(db.Boolean, nullable=False)
    
    # NEW: Emotion predictions
    emotion = db.Column(db.String(20), nullable=True)  # happy, sad, angry, surprised, neutral, fear, disgust
    emotion_confidence = db.Column(db.Float, nullable=True)  # Confidence score
    emotion_scores = db.Column(db.Text, nullable=True)  # JSON string with all emotion scores
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert prediction object to dictionary"""
        import json
        result = {
            'id': self.id,
            'user_id': self.user_id,
            'age_prediction': self.age_prediction,
            'smile_percentage': self.smile_percentage,
            'is_smiling': self.is_smiling,
            'created_at': self.created_at.isoformat()
        }
        
        # Add new fields if available
        if self.exact_age is not None:
            result['exact_age'] = self.exact_age
        if self.age_confidence is not None:
            result['age_confidence'] = round(self.age_confidence, 2)
        if self.emotion:
            result['emotion'] = self.emotion
        if self.emotion_confidence is not None:
            result['emotion_confidence'] = round(self.emotion_confidence, 2)
        if self.emotion_scores:
            try:
                result['emotion_scores'] = json.loads(self.emotion_scores)
            except:
                pass
        
        return result
