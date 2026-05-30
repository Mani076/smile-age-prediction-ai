"""
Module 6: Report Generation Module
Handles PDF report generation for predictions
"""

from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Prediction, User
from datetime import datetime
import os
from io import BytesIO

# Try to import reportlab for PDF generation
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    REPORTLAB_AVAILABLE = True
except ImportError:
    print("Warning: reportlab not available - report generation disabled")
    REPORTLAB_AVAILABLE = False

report_module = Blueprint('report_module', __name__, url_prefix='/api/reports')


class ReportService:
    """Service class for report generation operations"""
    
    @staticmethod
    def generate_prediction_report(user_id, prediction_id):
        """Generate PDF report for a specific prediction"""
        if not REPORTLAB_AVAILABLE:
            return {'error': 'Report generation not available - install reportlab'}, 503
        
        try:
            # Get prediction data
            prediction = Prediction.query.filter_by(
                id=prediction_id,
                user_id=user_id
            ).first()
            
            if not prediction:
                return {'error': 'Prediction not found'}, 404
            
            # Get user data
            user = User.query.get(user_id)
            
            # Create PDF in memory
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            elements = []
            
            # Styles
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#6366f1'),
                spaceAfter=30,
                alignment=TA_CENTER
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=16,
                textColor=colors.HexColor('#4f46e5'),
                spaceAfter=12,
                spaceBefore=12
            )
            
            # Title
            title = Paragraph("Smile & Age Prediction Report", title_style)
            elements.append(title)
            elements.append(Spacer(1, 0.3*inch))
            
            # User Information
            user_heading = Paragraph("User Information", heading_style)
            elements.append(user_heading)
            
            user_data = [
                ['Name:', f"{user.first_name} {user.last_name}"],
                ['Email:', user.email],
                ['Report Date:', datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')]
            ]
            
            user_table = Table(user_data, colWidths=[2*inch, 4*inch])
            user_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb'))
            ]))
            elements.append(user_table)
            elements.append(Spacer(1, 0.3*inch))
            
            # Prediction Results
            results_heading = Paragraph("Prediction Results", heading_style)
            elements.append(results_heading)
            
            prediction_data = [
                ['Prediction ID:', str(prediction.id)],
                ['Age Prediction:', prediction.age_prediction],
                ['Smile Detected:', 'Yes' if prediction.is_smiling else 'No'],
                ['Smile Confidence:', f"{prediction.smile_percentage}%"],
                ['Analysis Date:', prediction.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')]
            ]
            
            prediction_table = Table(prediction_data, colWidths=[2*inch, 4*inch])
            prediction_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb'))
            ]))
            elements.append(prediction_table)
            elements.append(Spacer(1, 0.3*inch))
            
            # Summary
            summary_heading = Paragraph("Summary", heading_style)
            elements.append(summary_heading)
            
            summary_text = f"""
            This report contains the results of an AI-powered smile and age detection analysis.
            The prediction was performed on {prediction.created_at.strftime('%B %d, %Y at %H:%M UTC')}.
            The analysis detected {'a smile' if prediction.is_smiling else 'no smile'} with 
            {prediction.smile_percentage}% confidence and predicted the age range as {prediction.age_prediction}.
            """
            
            summary_para = Paragraph(summary_text, styles['Normal'])
            elements.append(summary_para)
            elements.append(Spacer(1, 0.3*inch))
            
            # Footer
            footer_text = "Generated by AI Smile & Age Prediction System | Confidential"
            footer = Paragraph(footer_text, ParagraphStyle(
                'Footer',
                parent=styles['Normal'],
                fontSize=8,
                textColor=colors.grey,
                alignment=TA_CENTER
            ))
            elements.append(Spacer(1, 0.5*inch))
            elements.append(footer)
            
            # Build PDF
            doc.build(elements)
            buffer.seek(0)
            
            return buffer, None
            
        except Exception as e:
            return None, str(e)
    
    @staticmethod
    def generate_user_summary_report(user_id):
        """Generate summary report for all user predictions"""
        if not REPORTLAB_AVAILABLE:
            return {'error': 'Report generation not available - install reportlab'}, 503
        
        try:
            user = User.query.get(user_id)
            if not user:
                return {'error': 'User not found'}, 404
            
            predictions = Prediction.query.filter_by(user_id=user_id).all()
            
            if not predictions:
                return {'error': 'No predictions found for this user'}, 404
            
            # Create PDF
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            elements = []
            
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#6366f1'),
                spaceAfter=30,
                alignment=TA_CENTER
            )
            
            # Title
            title = Paragraph("User Prediction Summary Report", title_style)
            elements.append(title)
            elements.append(Spacer(1, 0.3*inch))
            
            # User info
            user_info = f"""
            <b>User:</b> {user.first_name} {user.last_name}<br/>
            <b>Email:</b> {user.email}<br/>
            <b>Total Predictions:</b> {len(predictions)}<br/>
            <b>Report Generated:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
            """
            elements.append(Paragraph(user_info, styles['Normal']))
            elements.append(Spacer(1, 0.3*inch))
            
            # Statistics
            smile_count = sum(1 for p in predictions if p.is_smiling)
            avg_smile_confidence = sum(p.smile_percentage for p in predictions) / len(predictions)
            
            stats_data = [
                ['Total Predictions', str(len(predictions))],
                ['Smiling Predictions', str(smile_count)],
                ['Non-Smiling Predictions', str(len(predictions) - smile_count)],
                ['Smile Percentage', f"{(smile_count/len(predictions)*100):.1f}%"],
                ['Avg Smile Confidence', f"{avg_smile_confidence:.1f}%"]
            ]
            
            stats_table = Table(stats_data, colWidths=[3*inch, 2*inch])
            stats_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6366f1')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(stats_table)
            
            # Build PDF
            doc.build(elements)
            buffer.seek(0)
            
            return buffer, None
            
        except Exception as e:
            return None, str(e)


# Routes
@report_module.route('/prediction/<int:prediction_id>', methods=['GET'])
@jwt_required()
def download_prediction_report(prediction_id):
    """Download PDF report for a specific prediction"""
    user_id = get_jwt_identity()
    
    buffer, error = ReportService.generate_prediction_report(user_id, prediction_id)
    
    if error:
        return jsonify({'error': error}), 500
    
    if isinstance(buffer, dict):
        return jsonify(buffer), buffer.get('status', 400)
    
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'prediction_report_{prediction_id}.pdf'
    )


@report_module.route('/summary', methods=['GET'])
@jwt_required()
def download_summary_report():
    """Download summary report for all user predictions"""
    user_id = get_jwt_identity()
    
    buffer, error = ReportService.generate_user_summary_report(user_id)
    
    if error:
        return jsonify({'error': error}), 500
    
    if isinstance(buffer, dict):
        return jsonify(buffer), buffer.get('status', 400)
    
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'user_summary_report_{user_id}.pdf'
    )


@report_module.route('/list', methods=['GET'])
@jwt_required()
def list_available_reports():
    """List all available reports for the user"""
    user_id = get_jwt_identity()
    
    try:
        predictions = Prediction.query.filter_by(user_id=user_id).all()
        
        reports = [
            {
                'prediction_id': p.id,
                'age_prediction': p.age_prediction,
                'is_smiling': p.is_smiling,
                'created_at': p.created_at.isoformat(),
                'report_url': f'/api/reports/prediction/{p.id}'
            }
            for p in predictions
        ]
        
        return jsonify({
            'total_reports': len(reports),
            'reports': reports,
            'summary_report_url': '/api/reports/summary'
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
