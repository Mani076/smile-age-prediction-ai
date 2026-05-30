"""
Module 5: Analytics Module
Handles advanced analytics, reports, and insights
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Prediction, User
from sqlalchemy import func, and_, extract
from datetime import datetime, timedelta
import json

analytics_module = Blueprint('analytics_module', __name__, url_prefix='/api/analytics')


class AnalyticsService:
    """Service class for analytics and reporting operations"""
    
    @staticmethod
    def get_smile_trends(user_id, days=7):
        """Get smile trends over time"""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Get daily average smile percentage
            daily_trends = db.session.query(
                func.date(Prediction.created_at).label('date'),
                func.avg(Prediction.smile_percentage).label('avg_smile'),
                func.count(Prediction.id).label('count')
            ).filter(
                Prediction.user_id == user_id,
                Prediction.created_at >= start_date
            ).group_by(func.date(Prediction.created_at))\
             .order_by(func.date(Prediction.created_at))\
             .all()
            
            trends = [
                {
                    'date': str(date),
                    'average_smile': round(float(avg_smile), 2),
                    'prediction_count': count
                }
                for date, avg_smile, count in daily_trends
            ]
            
            return {
                'trends': trends,
                'period_days': days,
                'start_date': start_date.isoformat()
            }, 200
            
        except Exception as e:
            return {'error': str(e)}, 500
    
    @staticmethod
    def get_hourly_distribution(user_id):
        """Get prediction distribution by hour of day"""
        try:
            hourly_dist = db.session.query(
                extract('hour', Prediction.created_at).label('hour'),
                func.count(Prediction.id).label('count'),
                func.avg(Prediction.smile_percentage).label('avg_smile')
            ).filter_by(user_id=user_id)\
             .group_by(extract('hour', Prediction.created_at))\
             .order_by(extract('hour', Prediction.created_at))\
             .all()
            
            distribution = [
                {
                    'hour': int(hour),
                    'prediction_count': count,
                    'average_smile': round(float(avg_smile), 2)
                }
                for hour, count, avg_smile in hourly_dist
            ]
            
            return {'hourly_distribution': distribution}, 200
            
        except Exception as e:
            return {'error': str(e)}, 500
    
    @staticmethod
    def get_age_smile_correlation(user_id):
        """Get correlation between predicted age and smile percentage"""
        try:
            age_smile_data = db.session.query(
                Prediction.age_prediction,
                func.avg(Prediction.smile_percentage).label('avg_smile'),
                func.count(Prediction.id).label('count')
            ).filter_by(user_id=user_id)\
             .group_by(Prediction.age_prediction)\
             .all()
            
            correlation = [
                {
                    'age_range': age,
                    'average_smile': round(float(avg_smile), 2),
                    'sample_count': count
                }
                for age, avg_smile, count in age_smile_data
            ]
            
            return {'age_smile_correlation': correlation}, 200
            
        except Exception as e:
            return {'error': str(e)}, 500
    
    @staticmethod
    def get_comprehensive_report(user_id):
        """Get comprehensive analytics report"""
        try:
            # Basic statistics
            total_predictions = Prediction.query.filter_by(user_id=user_id).count()
            
            if total_predictions == 0:
                return {
                    'message': 'No predictions available for analysis',
                    'total_predictions': 0
                }, 200
            
            # Smile statistics
            smiling_count = Prediction.query.filter_by(user_id=user_id, is_smiling=True).count()
            avg_smile = db.session.query(func.avg(Prediction.smile_percentage))\
                .filter_by(user_id=user_id).scalar()
            max_smile = db.session.query(func.max(Prediction.smile_percentage))\
                .filter_by(user_id=user_id).scalar()
            min_smile = db.session.query(func.min(Prediction.smile_percentage))\
                .filter_by(user_id=user_id).scalar()
            
            # Age distribution
            age_dist = db.session.query(
                Prediction.age_prediction,
                func.count(Prediction.id)
            ).filter_by(user_id=user_id)\
             .group_by(Prediction.age_prediction)\
             .all()
            
            # Most common age
            most_common_age = max(age_dist, key=lambda x: x[1])[0] if age_dist else None
            
            # Recent activity
            last_prediction = Prediction.query.filter_by(user_id=user_id)\
                .order_by(Prediction.created_at.desc()).first()
            first_prediction = Prediction.query.filter_by(user_id=user_id)\
                .order_by(Prediction.created_at.asc()).first()
            
            # Calculate activity span
            if first_prediction and last_prediction:
                activity_span = (last_prediction.created_at - first_prediction.created_at).days
            else:
                activity_span = 0
            
            report = {
                'summary': {
                    'total_predictions': total_predictions,
                    'smiling_count': smiling_count,
                    'not_smiling_count': total_predictions - smiling_count,
                    'smiling_rate': round((smiling_count / total_predictions * 100), 2),
                    'activity_span_days': activity_span
                },
                'smile_metrics': {
                    'average': round(float(avg_smile), 2),
                    'maximum': int(max_smile),
                    'minimum': int(min_smile),
                    'range': int(max_smile - min_smile)
                },
                'age_analysis': {
                    'distribution': {age: count for age, count in age_dist},
                    'most_common_age': most_common_age
                },
                'activity': {
                    'first_prediction': first_prediction.created_at.isoformat() if first_prediction else None,
                    'last_prediction': last_prediction.created_at.isoformat() if last_prediction else None,
                    'average_predictions_per_day': round(total_predictions / max(activity_span, 1), 2)
                }
            }
            
            return {'report': report}, 200
            
        except Exception as e:
            return {'error': str(e)}, 500
    
    @staticmethod
    def compare_with_average(user_id):
        """Compare user statistics with platform average"""
        try:
            # User statistics
            user_avg_smile = db.session.query(func.avg(Prediction.smile_percentage))\
                .filter_by(user_id=user_id).scalar() or 0
            user_total = Prediction.query.filter_by(user_id=user_id).count()
            
            # Platform statistics
            platform_avg_smile = db.session.query(func.avg(Prediction.smile_percentage)).scalar() or 0
            platform_total = Prediction.query.count()
            total_users = User.query.count()
            
            comparison = {
                'user_metrics': {
                    'average_smile': round(float(user_avg_smile), 2),
                    'total_predictions': user_total
                },
                'platform_metrics': {
                    'average_smile': round(float(platform_avg_smile), 2),
                    'total_predictions': platform_total,
                    'total_users': total_users,
                    'average_predictions_per_user': round(platform_total / max(total_users, 1), 2)
                },
                'comparison': {
                    'smile_difference': round(float(user_avg_smile - platform_avg_smile), 2),
                    'above_average': user_avg_smile > platform_avg_smile
                }
            }
            
            return {'comparison': comparison}, 200
            
        except Exception as e:
            return {'error': str(e)}, 500


# Routes
@analytics_module.route('/trends', methods=['GET'])
@jwt_required()
def get_trends():
    """Get smile trends over time"""
    user_id = get_jwt_identity()
    days = request.args.get('days', 7, type=int)
    result, status_code = AnalyticsService.get_smile_trends(user_id, days)
    return jsonify(result), status_code


@analytics_module.route('/hourly-distribution', methods=['GET'])
@jwt_required()
def get_hourly_distribution():
    """Get hourly prediction distribution"""
    user_id = get_jwt_identity()
    result, status_code = AnalyticsService.get_hourly_distribution(user_id)
    return jsonify(result), status_code


@analytics_module.route('/age-smile-correlation', methods=['GET'])
@jwt_required()
def get_age_smile_correlation():
    """Get age-smile correlation"""
    user_id = get_jwt_identity()
    result, status_code = AnalyticsService.get_age_smile_correlation(user_id)
    return jsonify(result), status_code


@analytics_module.route('/report', methods=['GET'])
@jwt_required()
def get_comprehensive_report():
    """Get comprehensive analytics report"""
    user_id = get_jwt_identity()
    result, status_code = AnalyticsService.get_comprehensive_report(user_id)
    return jsonify(result), status_code


@analytics_module.route('/compare', methods=['GET'])
@jwt_required()
def compare_with_average():
    """Compare user statistics with platform average"""
    user_id = get_jwt_identity()
    result, status_code = AnalyticsService.compare_with_average(user_id)
    return jsonify(result), status_code


@analytics_module.route('/export', methods=['GET'])
@jwt_required()
def export_data():
    """Export user data as JSON"""
    user_id = get_jwt_identity()
    
    try:
        # Get all user predictions
        predictions = Prediction.query.filter_by(user_id=user_id).all()
        
        # Get user info
        user = User.query.get(user_id)
        
        export_data = {
            'user': user.to_dict(),
            'predictions': [p.to_dict() for p in predictions],
            'export_date': datetime.utcnow().isoformat(),
            'total_predictions': len(predictions)
        }
        
        return jsonify({
            'data': export_data,
            'message': 'Data exported successfully'
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
