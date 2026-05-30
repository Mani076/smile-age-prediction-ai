"""
Module 2: User Management Module
Handles user profile operations, updates, and account management
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User
import re

user_module = Blueprint('user_module', __name__, url_prefix='/api/user')


class UserService:
    """Service class for user management operations"""
    
    @staticmethod
    def validate_phone(phone):
        """Validate phone number format"""
        pattern = r'^\+?1?\d{9,15}$'
        return re.match(pattern, phone) is not None
    
    @staticmethod
    def get_user_profile(user_id):
        """Get user profile by ID"""
        try:
            user = User.query.get(user_id)
            
            if not user:
                return {'error': 'User not found'}, 404
            
            return {'user': user.to_dict()}, 200
            
        except Exception as e:
            return {'error': str(e)}, 500
    
    @staticmethod
    def update_user_profile(user_id, data):
        """Update user profile"""
        try:
            user = User.query.get(user_id)
            
            if not user:
                return {'error': 'User not found'}, 404
            
            # Update allowed fields
            if 'first_name' in data:
                user.first_name = data['first_name'].strip()
            if 'last_name' in data:
                user.last_name = data['last_name'].strip()
            if 'phone_number' in data:
                if not UserService.validate_phone(data['phone_number']):
                    return {'error': 'Invalid phone number format'}, 400
                user.phone_number = data['phone_number'].strip()
            
            db.session.commit()
            
            return {
                'message': 'Profile updated successfully',
                'user': user.to_dict()
            }, 200
            
        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 500
    
    @staticmethod
    def delete_user_account(user_id):
        """Soft delete user account (deactivate)"""
        try:
            user = User.query.get(user_id)
            
            if not user:
                return {'error': 'User not found'}, 404
            
            user.is_active = False
            db.session.commit()
            
            return {'message': 'Account deactivated successfully'}, 200
            
        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 500
    
    @staticmethod
    def get_all_users(page=1, per_page=10):
        """Get all users with pagination (admin function)"""
        try:
            users = User.query.paginate(page=page, per_page=per_page, error_out=False)
            
            return {
                'users': [user.to_dict() for user in users.items],
                'total': users.total,
                'pages': users.pages,
                'current_page': page
            }, 200
            
        except Exception as e:
            return {'error': str(e)}, 500


# Routes
@user_module.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Get current user profile"""
    user_id = int(get_jwt_identity())
    result, status_code = UserService.get_user_profile(user_id)
    return jsonify(result), status_code


@user_module.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Update user profile"""
    user_id = int(get_jwt_identity())
    data = request.get_json()
    result, status_code = UserService.update_user_profile(user_id, data)
    return jsonify(result), status_code


@user_module.route('/profile', methods=['DELETE'])
@jwt_required()
def delete_account():
    """Delete user account (soft delete)"""
    user_id = int(get_jwt_identity())
    result, status_code = UserService.delete_user_account(user_id)
    return jsonify(result), status_code


@user_module.route('/list', methods=['GET'])
@jwt_required()
def list_users():
    """Get all users (admin function)"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    result, status_code = UserService.get_all_users(page, per_page)
    return jsonify(result), status_code
