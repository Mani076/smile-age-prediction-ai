"""
Module 7: Admin Module
Handles administrative operations and system monitoring
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, Prediction
from functools import wraps
from datetime import datetime, timedelta
from sqlalchemy import func

admin_module = Blueprint('admin_module', __name__, url_prefix='/api/admin')


def admin_required(fn):
    """Decorator to require admin role"""
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        # Check if user has admin role (you'll need to add role field to User model)
        # For now, we'll check if email contains 'admin'
        if not user or 'admin' not in user.email.lower():
            return jsonify({'error': 'Admin access required'}), 403
        
        return fn(*args, **kwargs)
    return wrapper


class AdminService:
    """Service class for admin operations"""
    
    @staticmethod
    def get_all_users(page=1, per_page=20):
        """Get all users with pagination"""
        try:
            users = User.query.paginate(
                page=page,
                per_page=per_page,
                error_out=False
            )
            
            return {
                'users': [user.to_dict() for user in users.items],
                'total': users.total,
                'pages': users.pages,
                'current_page': page,
                'per_page': per_page
            }, 200
            
        except Exception as e:
            return {'error': str(e)}, 500
    
    @staticmethod
    def get_user_details(user_id):
        """Get detailed information about a specific user"""
        try:
            user = User.query.get(user_id)
            if not user:
                return {'error': 'User not found'}, 404
            
            # Get user's predictions
            predictions = Prediction.query.filter_by(user_id=user_id).all()
            
            # Calculate statistics
            total_predictions = len(predictions)
            smile_count = sum(1 for p in predictions if p.is_smiling)
            
            return {
                'user': user.to_dict(),
                'statistics': {
                    'total_predictions': total_predictions,
                    'smile_count': smile_count,
                    'non_smile_count': total_predictions - smile_count,
                    'smile_percentage': (smile_count / total_predictions * 100) if total_predictions > 0 else 0
                },
                'recent_predictions': [p.to_dict() for p in predictions[-5:]]
            }, 200
            
        except Exception as e:
            return {'error': str(e)}, 500
    
    @staticmethod
    def get_all_predictions(page=1, per_page=50):
        """Get all predictions across all users"""
        try:
            predictions = Prediction.query.order_by(
                Prediction.created_at.desc()
            ).paginate(
                page=page,
                per_page=per_page,
                error_out=False
            )
            
            return {
                'predictions': [p.to_dict() for p in predictions.items],
                'total': predictions.total,
                'pages': predictions.pages,
                'current_page': page,
                'per_page': per_page
            }, 200
            
        except Exception as e:
            return {'error': str(e)}, 500
    
    @staticmethod
    def delete_user(user_id):
        """Delete a user and all their predictions"""
        try:
            user = User.query.get(user_id)
            if not user:
                return {'error': 'User not found'}, 404
            
            # Delete all user's predictions
            Prediction.query.filter_by(user_id=user_id).delete()
            
            # Delete user
            db.session.delete(user)
            db.session.commit()
            
            return {'message': 'User and all associated data deleted successfully'}, 200
            
        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 500
    
    @staticmethod
    def delete_prediction(prediction_id):
        """Delete a specific prediction"""
        try:
            prediction = Prediction.query.get(prediction_id)
            if not prediction:
                return {'error': 'Prediction not found'}, 404
            
            db.session.delete(prediction)
            db.session.commit()
            
            return {'message': 'Prediction deleted successfully'}, 200
            
        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 500
    
    @staticmethod
    def get_system_statistics():
        """Get overall system statistics"""
        try:
            # User statistics
            total_users = User.query.count()
            active_users = User.query.filter_by(is_active=True).count()
            
            # Prediction statistics
            total_predictions = Prediction.query.count()
            
            # Get predictions from last 7 days
            seven_days_ago = datetime.utcnow() - timedelta(days=7)
            recent_predictions = Prediction.query.filter(
                Prediction.created_at >= seven_days_ago
            ).count()
            
            # Smile statistics
            smile_predictions = Prediction.query.filter_by(is_smiling=True).count()
            
            # Age distribution
            age_distribution = db.session.query(
                Prediction.age_prediction,
                func.count(Prediction.id)
            ).group_by(Prediction.age_prediction).all()
            
            # Daily predictions (last 7 days)
            daily_stats = []
            for i in range(7):
                date = datetime.utcnow() - timedelta(days=i)
                start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
                end_of_day = start_of_day + timedelta(days=1)
                
                count = Prediction.query.filter(
                    Prediction.created_at >= start_of_day,
                    Prediction.created_at < end_of_day
                ).count()
                
                daily_stats.append({
                    'date': start_of_day.strftime('%Y-%m-%d'),
                    'count': count
                })
            
            return {
                'users': {
                    'total': total_users,
                    'active': active_users,
                    'inactive': total_users - active_users
                },
                'predictions': {
                    'total': total_predictions,
                    'last_7_days': recent_predictions,
                    'smiling': smile_predictions,
                    'not_smiling': total_predictions - smile_predictions,
                    'smile_percentage': (smile_predictions / total_predictions * 100) if total_predictions > 0 else 0
                },
                'age_distribution': [
                    {'age_range': age, 'count': count}
                    for age, count in age_distribution
                ],
                'daily_predictions': daily_stats
            }, 200
            
        except Exception as e:
            return {'error': str(e)}, 500
    
    @staticmethod
    def get_api_usage_stats():
        """Get API usage statistics"""
        try:
            # Get predictions per user
            user_stats = db.session.query(
                User.email,
                func.count(Prediction.id).label('prediction_count')
            ).join(Prediction).group_by(User.email).order_by(
                func.count(Prediction.id).desc()
            ).limit(10).all()
            
            # Get hourly distribution
            hourly_stats = db.session.query(
                func.strftime('%H', Prediction.created_at).label('hour'),
                func.count(Prediction.id).label('count')
            ).group_by('hour').all()
            
            return {
                'top_users': [
                    {'email': email, 'predictions': count}
                    for email, count in user_stats
                ],
                'hourly_distribution': [
                    {'hour': int(hour), 'count': count}
                    for hour, count in hourly_stats
                ]
            }, 200
            
        except Exception as e:
            return {'error': str(e)}, 500


# Routes
@admin_module.route('/users', methods=['GET'])
@admin_required
def get_all_users():
    """Get all users (admin only)"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    result, status_code = AdminService.get_all_users(page, per_page)
    return jsonify(result), status_code


@admin_module.route('/users/<int:user_id>', methods=['GET'])
@admin_required
def get_user_details(user_id):
    """Get detailed user information (admin only)"""
    result, status_code = AdminService.get_user_details(user_id)
    return jsonify(result), status_code


@admin_module.route('/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    """Delete a user (admin only)"""
    result, status_code = AdminService.delete_user(user_id)
    return jsonify(result), status_code


@admin_module.route('/predictions', methods=['GET'])
@admin_required
def get_all_predictions():
    """Get all predictions (admin only)"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    result, status_code = AdminService.get_all_predictions(page, per_page)
    return jsonify(result), status_code


@admin_module.route('/predictions/<int:prediction_id>', methods=['DELETE'])
@admin_required
def delete_prediction(prediction_id):
    """Delete a prediction (admin only)"""
    result, status_code = AdminService.delete_prediction(prediction_id)
    return jsonify(result), status_code


@admin_module.route('/statistics', methods=['GET'])
@admin_required
def get_system_statistics():
    """Get system-wide statistics (admin only)"""
    result, status_code = AdminService.get_system_statistics()
    return jsonify(result), status_code


@admin_module.route('/api-usage', methods=['GET'])
@admin_required
def get_api_usage():
    """Get API usage statistics (admin only)"""
    result, status_code = AdminService.get_api_usage_stats()
    return jsonify(result), status_code


@admin_module.route('/dashboard', methods=['GET'])
@admin_required
def get_admin_dashboard():
    """Get complete admin dashboard data (admin only)"""
    try:
        system_stats, _ = AdminService.get_system_statistics()
        api_usage, _ = AdminService.get_api_usage_stats()
        
        return jsonify({
            'system_statistics': system_stats,
            'api_usage': api_usage,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
