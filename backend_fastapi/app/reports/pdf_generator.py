"""
PDF report generation using ReportLab
"""
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from datetime import datetime
from pathlib import Path


def generate_prediction_report(prediction, user, output_path: str):
    """
    Generate comprehensive PDF report for prediction
    
    Args:
        prediction: Prediction model instance
        user: User model instance
        output_path: Path to save PDF
    """
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=18
    )
    
    # Container for elements
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#2C3E50'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#34495E'),
        spaceAfter=12,
        spaceBefore=12
    )
    
    # Title
    title = Paragraph("AI Image Analysis Report", title_style)
    elements.append(title)
    elements.append(Spacer(1, 0.2*inch))
    
    # User Information
    user_info = [
        ["Report Generated For:", f"{user.first_name} {user.last_name}"],
        ["Email:", user.email],
        ["Generated On:", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")],
        ["Prediction ID:", str(prediction.id)]
    ]
    
    user_table = Table(user_info, colWidths=[2*inch, 4*inch])
    user_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ECF0F1')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey)
    ]))
    
    elements.append(user_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Summary Section
    summary_heading = Paragraph("Analysis Summary", heading_style)
    elements.append(summary_heading)
    
    summary_data = [
        ["Metric", "Value"],
        ["Faces Detected", str(prediction.num_faces)],
        ["Average Age", f"{prediction.avg_age:.1f} years" if prediction.avg_age else "N/A"],
        ["Smiling Faces", f"{prediction.smile_count} / {prediction.num_faces}"],
        ["Dominant Emotion", prediction.dominant_emotion or "N/A"],
        ["Model Version", prediction.model_version],
        ["Processing Time", f"{prediction.processing_time:.2f} seconds"]
    ]
    
    summary_table = Table(summary_data, colWidths=[2.5*inch, 3.5*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498DB')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey)
    ]))
    
    elements.append(summary_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Detailed Face Analysis
    if prediction.num_faces > 0:
        faces_heading = Paragraph("Detailed Face Analysis", heading_style)
        elements.append(faces_heading)
        
        for face in prediction.faces_data:
            face_data = [
                ["Face ID", str(face['face_id'])],
                ["Age", f"{face['age']} years ({face['age_range']})"],
                ["Smile", f"{'Yes' if face['smile'] else 'No'} (Confidence: {face['smile_confidence']:.1%})"],
                ["Emotion", f"{face['emotion']} (Confidence: {face['emotion_confidence']:.1%})"],
                ["Position", f"X: {face['bounding_box']['x']}, Y: {face['bounding_box']['y']}"]
            ]
            
            face_table = Table(face_data, colWidths=[1.5*inch, 4.5*inch])
            face_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E8F8F5')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey)
            ]))
            
            elements.append(face_table)
            elements.append(Spacer(1, 0.15*inch))
    
    # Footer
    elements.append(Spacer(1, 0.3*inch))
    footer_text = Paragraph(
        "<i>This report was automatically generated by AI Image Analysis Tool. "
        "Results are based on machine learning predictions and should be used for reference only.</i>",
        styles['Normal']
    )
    elements.append(footer_text)
    
    # Build PDF
    doc.build(elements)
