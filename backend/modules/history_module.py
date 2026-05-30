"""
Module 4: History Module
Handles prediction history, statistics, and analytics
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Prediction
from sqlalchemy import func
from datetime import datetime, timedelta

history_module = Blueprint('history_module', __name__, url_prefix='/api/history')


class HistoryService:
    """Service class for history and analytics operations"""
    
    @staticmethod
    def get_user_history(user_id, page=1, per_page=10, filter_smiling=None):
        """Get user's prediction history with optional filtering"""
        try:
            query = Prediction.query.filter_by(user_id=user_id)
            
            # Apply filter if specified
            if filter_smiling is not None:
                query = query.filter_by(is_smiling=filter_smiling)
            
            predictions = query.order_by(Prediction.created_at.desc())\
                .paginate(page=page, per_page=per_page, error_out=False)
            
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
    def get_user_statistics(user_id):
        """Get user's prediction statistics"""
        try:
            total_predictions = Prediction.query.filter_by(user_id=user_id).count()
            smiling_count = Prediction.query.filter_by(user_id=user_id, is_smiling=True).count()
            not_smiling_count = total_predictions - smiling_count
            
            avg_smile = db.session.query(func.avg(Prediction.smile_percentage))\
                .filter_by(user_id=user_id).scalar() or 0
            
            # Age distribution
            age_distribution = db.session.query(
                Prediction.age_prediction,
                func.count(Prediction.id)
            ).filter_by(user_id=user_id)\
             .group_by(Prediction.age_prediction)\
             .all()
            
            age_dist_dict = {age: count for age, count in age_distribution}
            
            return {
                'total_predictions': total_predictions,
                'smiling_count': smiling_count,
                'not_smiling_count': not_smiling_count,
                'smiling_percentage': round((smiling_count / total_predictions * 100), 2) if total_predictions > 0 else 0,
                'average_smile_percentage': round(avg_smile, 2),
                'age_distribution': age_dist_dict
            }, 200
            
        except Exception as e:
            return {'error': str(e)}, 500
    
    @staticmethod
    def get_recent_predictions(user_id, limit=5):
        """Get user's most recent predictions"""
        try:
            predictions = Prediction.query.filter_by(user_id=user_id)\
                .order_by(Prediction.created_at.desc())\
                .limit(limit)\
                .all()
            
            return {
                'recent_predictions': [p.to_dict() for p in predictions],
                'count': len(predictions)
            }, 200
            
        except Exception as e:
            return {'error': str(e)}, 500
    
    @staticmethod
    def get_predictions_by_date_range(user_id, start_date, end_date):
        """Get predictions within a date range"""
        try:
            predictions = Prediction.query.filter(
                Prediction.user_id == user_id,
                Prediction.created_at >= start_date,
                Prediction.created_at <= end_date
            ).order_by(Prediction.created_at.desc()).all()
            
            return {
                'predictions': [p.to_dict() for p in predictions],
                'count': len(predictions),
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            }, 200
            
        except Exception as e:
            return {'error': str(e)}, 500
    
    @staticmethod
    def delete_prediction(user_id, prediction_id):
        """Delete a specific prediction"""
        try:
            prediction = Prediction.query.filter_by(
                id=prediction_id,
                user_id=user_id
            ).first()
            
            if not prediction:
                return {'error': 'Prediction not found'}, 404
            
            db.session.delete(prediction)
            db.session.commit()
            
            return {'message': 'Prediction deleted successfully'}, 200
            
        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 500
    
    @staticmethod
    def clear_user_history(user_id):
        """Clear all predictions for a user"""
        try:
            deleted_count = Prediction.query.filter_by(user_id=user_id).delete()
            db.session.commit()
            
            return {
                'message': 'History cleared successfully',
                'deleted_count': deleted_count
            }, 200
            
        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 500


# Routes
@history_module.route('/predictions', methods=['GET'])
@jwt_required()
def get_history():
    """Get user's prediction history"""
    user_id = get_jwt_identity()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    filter_smiling = request.args.get('smiling', None, type=lambda v: v.lower() == 'true' if v else None)
    
    result, status_code = HistoryService.get_user_history(user_id, page, per_page, filter_smiling)
    return jsonify(result), status_code


@history_module.route('/statistics', methods=['GET'])
@jwt_required()
def get_statistics():
    """Get user's prediction statistics"""
    user_id = get_jwt_identity()
    result, status_code = HistoryService.get_user_statistics(user_id)
    return jsonify(result), status_code


@history_module.route('/recent', methods=['GET'])
@jwt_required()
def get_recent():
    """Get user's recent predictions"""
    user_id = get_jwt_identity()
    limit = request.args.get('limit', 5, type=int)
    result, status_code = HistoryService.get_recent_predictions(user_id, limit)
    return jsonify(result), status_code


@history_module.route('/date-range', methods=['GET'])
@jwt_required()
def get_by_date_range():
    """Get predictions by date range"""
    user_id = get_jwt_identity()
    
    try:
        start_date = datetime.fromisoformat(request.args.get('start_date'))
        end_date = datetime.fromisoformat(request.args.get('end_date'))
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid date format. Use ISO format (YYYY-MM-DD)'}), 400
    
    result, status_code = HistoryService.get_predictions_by_date_range(user_id, start_date, end_date)
    return jsonify(result), status_code


@history_module.route('/prediction/<int:prediction_id>', methods=['DELETE'])
@jwt_required()
def delete_prediction(prediction_id):
    """Delete a specific prediction"""
    user_id = get_jwt_identity()
    result, status_code = HistoryService.delete_prediction(user_id, prediction_id)
    return jsonify(result), status_code


@history_module.route('/clear', methods=['DELETE'])
@jwt_required()
def clear_history():
    """Clear all user history"""
    user_id = get_jwt_identity()
    result, status_code = HistoryService.clear_user_history(user_id)
    return jsonify(result), status_code
