"""
Report Generation Module for Rolevo
Generates PDF reports with scores and feedback for roleplay interactions
"""

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from datetime import datetime
import os


def generate_roleplay_report(user_name, user_email, roleplay_name, scenario, 
                             overall_score, score_breakdown, interactions, 
                             completion_date=None, output_path=None):
    """
    Generate a comprehensive roleplay performance report
    
    Args:
        user_name: Name of the user
        user_email: Email of the user
        roleplay_name: Name of the roleplay scenario
        scenario: Description of the roleplay scenario
        overall_score: Overall performance score (0-100)
        score_breakdown: Dict with score categories and values
        interactions: List of interaction dicts with user_text and response_text
        completion_date: Date of completion (defaults to now)
        output_path: Path to save the PDF (defaults to temp folder)
    
    Returns:
        Path to the generated PDF file
    """
    if completion_date is None:
        completion_date = datetime.now()
    
    if output_path is None:
        from flask import current_app
        temp_dir = os.path.join(current_app.root_path, 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = os.path.join(temp_dir, f'report_{user_email}_{timestamp}.pdf')
    
    # Create the PDF document
    doc = SimpleDocTemplate(output_path, pagesize=A4,
                           topMargin=0.5*inch, bottomMargin=0.5*inch,
                           leftMargin=0.75*inch, rightMargin=0.75*inch)
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#074924'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#074924'),
        spaceAfter=12,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    )
    
    subheading_style = ParagraphStyle(
        'CustomSubHeading',
        parent=styles['Heading3'],
        fontSize=12,
        textColor=colors.HexColor('#074924'),
        spaceAfter=6,
        fontName='Helvetica-Bold'
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=12,
        alignment=TA_JUSTIFY
    )
    
    # Title
    elements.append(Paragraph("ROLEVO", title_style))
    elements.append(Paragraph("Roleplay Performance Report", heading_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # User Information Table
    user_info_data = [
        ['Participant Name:', user_name],
        ['Email:', user_email],
        ['Report Date:', completion_date.strftime('%B %d, %Y')],
        ['Roleplay Scenario:', roleplay_name]
    ]
    
    user_info_table = Table(user_info_data, colWidths=[2*inch, 4*inch])
    user_info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#074924')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    
    elements.append(user_info_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Scenario Description
    elements.append(Paragraph("Scenario Description", heading_style))
    elements.append(Paragraph(scenario, normal_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Overall Score Section
    elements.append(Paragraph("Performance Summary", heading_style))
    
    # Create a colored box for overall score
    score_color = get_score_color(overall_score)
    score_data = [[f"Overall Score: {overall_score}/100"]]
    score_table = Table(score_data, colWidths=[6*inch])
    score_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), score_color),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 18),
        ('TOPPADDING', (0, 0), (-1, -1), 15),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
        ('BOX', (0, 0), (-1, -1), 2, colors.HexColor('#074924')),
    ]))
    
    elements.append(score_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # Score Breakdown
    if score_breakdown:
        elements.append(Paragraph("Detailed Score Breakdown", heading_style))
        
        breakdown_data = [['Criteria', 'Score', 'Rating']]
        for category, score in score_breakdown.items():
            rating = get_rating_text(score)
            breakdown_data.append([category, f"{score}/100", rating])
        
        breakdown_table = Table(breakdown_data, colWidths=[3*inch, 1.5*inch, 1.5*inch])
        breakdown_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#074924')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')])
        ]))
        
        elements.append(breakdown_table)
        elements.append(Spacer(1, 0.3*inch))
    
    # Interaction Transcript
    if interactions:
        elements.append(Paragraph("Interaction Transcript", heading_style))
        elements.append(Spacer(1, 0.1*inch))
        
        for idx, interaction in enumerate(interactions, 1):
            # User message
            elements.append(Paragraph(f"<b>Exchange {idx} - Your Response:</b>", subheading_style))
            elements.append(Paragraph(interaction.get('user_text', 'N/A'), normal_style))
            
            # System response
            elements.append(Paragraph(f"<b>Feedback:</b>", subheading_style))
            elements.append(Paragraph(interaction.get('response_text', 'N/A'), normal_style))
            elements.append(Spacer(1, 0.15*inch))
    
    # Performance Recommendations
    elements.append(PageBreak())
    elements.append(Paragraph("Performance Analysis & Recommendations", heading_style))
    
    recommendations = generate_recommendations(overall_score, score_breakdown)
    for rec in recommendations:
        elements.append(Paragraph(f"• {rec}", normal_style))
    
    elements.append(Spacer(1, 0.3*inch))
    
    # Footer
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.grey,
        alignment=TA_CENTER
    )
    
    elements.append(Spacer(1, 0.5*inch))
    elements.append(Paragraph("This report is confidential and intended for the named recipient only.", footer_style))
    elements.append(Paragraph("© 2025 ROLEVO - All Rights Reserved", footer_style))
    
    # Build PDF
    doc.build(elements)
    
    return output_path


def get_score_color(score):
    """Return color based on score"""
    if score >= 80:
        return colors.HexColor('#28a745')  # Green
    elif score >= 60:
        return colors.HexColor('#ffc107')  # Yellow
    elif score >= 40:
        return colors.HexColor('#ff9800')  # Orange
    else:
        return colors.HexColor('#dc3545')  # Red


def get_rating_text(score):
    """Return rating text based on score"""
    if score >= 90:
        return 'Excellent'
    elif score >= 80:
        return 'Very Good'
    elif score >= 70:
        return 'Good'
    elif score >= 60:
        return 'Satisfactory'
    elif score >= 50:
        return 'Fair'
    else:
        return 'Needs Improvement'


def generate_recommendations(overall_score, score_breakdown):
    """Generate personalized recommendations based on scores"""
    recommendations = []
    
    if overall_score >= 80:
        recommendations.append("Excellent performance! Continue maintaining this level of professionalism.")
        recommendations.append("Consider mentoring others who are developing their skills in this area.")
    elif overall_score >= 60:
        recommendations.append("Good performance with room for improvement in specific areas.")
    else:
        recommendations.append("Additional practice recommended to improve overall performance.")
    
    # Analyze specific categories
    if score_breakdown:
        low_scores = {k: v for k, v in score_breakdown.items() if v < 60}
        
        if low_scores:
            recommendations.append(f"Focus on improving: {', '.join(low_scores.keys())}")
            
        high_scores = {k: v for k, v in score_breakdown.items() if v >= 80}
        if high_scores:
            recommendations.append(f"Strong areas to leverage: {', '.join(high_scores.keys())}")
    
    recommendations.append("Review the interaction transcript to identify specific moments for improvement.")
    recommendations.append("Practice active listening and empathetic responses in future interactions.")
    recommendations.append("Consider scheduling a follow-up session to track progress.")
    
    return recommendations
