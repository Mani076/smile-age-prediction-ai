"""
Module 1: Authentication Module
Handles user authentication, registration, and session management
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from email_validator import validate_email, EmailNotValidError
from models import db, User
import re

auth_module = Blueprint('auth_module', __name__, url_prefix='/api/auth')


class AuthService:
    """Service class for authentication operations"""
    
    @staticmethod
    def validate_phone(phone):
        """Validate phone number format"""
        pattern = r'^\+?1?\d{9,15}$'
        return re.match(pattern, phone) is not None
    
    @staticmethod
    def validate_password(password):
        """Validate password strength"""
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        if not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter"
        if not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter"
        if not re.search(r'\d', password):
            return False, "Password must contain at least one digit"
        return True, "Password is valid"
    
    @staticmethod
    def register_user(data):
        """Register a new user"""
        try:
            # Validate required fields
            required_fields = ['first_name', 'last_name', 'email', 'phone_number', 'password', 'confirm_password']
            for field in required_fields:
                if field not in data or not data[field]:
                    return {'error': f'{field} is required'}, 400
            
            # Validate email
            try:
                valid = validate_email(data['email'], check_deliverability=False)
                email = valid.email
            except EmailNotValidError as e:
                return {'error': str(e)}, 400
            
            # Validate phone number
            if not AuthService.validate_phone(data['phone_number']):
                return {'error': 'Invalid phone number format'}, 400
            
            # Validate password match
            if data['password'] != data['confirm_password']:
                return {'error': 'Passwords do not match'}, 400
            
            # Validate password strength
            is_valid, message = AuthService.validate_password(data['password'])
            if not is_valid:
                return {'error': message}, 400
            
            # Check if user already exists
            if User.query.filter_by(email=email).first():
                return {'error': 'Email already registered'}, 409
            
            # Create new user
            user = User(
                first_name=data['first_name'].strip(),
                last_name=data['last_name'].strip(),
                email=email,
                phone_number=data['phone_number'].strip()
            )
            user.set_password(data['password'])
            
            db.session.add(user)
            db.session.commit()
            
            return {
                'message': 'User registered successfully',
                'user': user.to_dict()
            }, 201
            
        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 500
    
    @staticmethod
    def login_user(data):
        """Login user and return JWT token"""
        try:
            # Validate required fields
            if not data.get('email') or not data.get('password'):
                return {'error': 'Email and password are required'}, 400
            
            # Find user
            user = User.query.filter_by(email=data['email']).first()
            
            if not user or not user.check_password(data['password']):
                return {'error': 'Invalid email or password'}, 401
            
            if not user.is_active:
                return {'error': 'Account is deactivated'}, 403
            
            # Create access token
            access_token = create_access_token(identity=str(user.id))
            
            return {
                'message': 'Login successful',
                'access_token': access_token,
                'user': user.to_dict()
            }, 200
            
        except Exception as e:
            return {'error': str(e)}, 500


# Routes
@auth_module.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    data = request.get_json()
    result, status_code = AuthService.register_user(data)
    return jsonify(result), status_code


@auth_module.route('/login', methods=['POST'])
def login():
    """Login user and return JWT token"""
    data = request.get_json()
    result, status_code = AuthService.login_user(data)
    return jsonify(result), status_code


@auth_module.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """Logout user (client-side token removal)"""
    return jsonify({'message': 'Logout successful'}), 200
