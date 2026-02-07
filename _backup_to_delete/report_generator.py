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
from datetime import datetime, timezone, timedelta
import os
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
from io import BytesIO

# IST Timezone (UTC+5:30) - India Standard Time
IST = timezone(timedelta(hours=5, minutes=30))
# Database server timezone (UTC+4) - Gulf Standard Time (Dubai)
DB_SERVER_TZ = timezone(timedelta(hours=4))

def get_ist_now():
    """Get current datetime in IST timezone (server-independent)"""
    # Always use UTC as base and convert to IST - works regardless of local machine
    return datetime.now(timezone.utc).astimezone(IST)

def convert_to_ist(dt):
    """Convert a datetime to IST. Handles naive and aware datetimes.
    
    For naive datetimes (no timezone info), we assume they are in database server time (UTC+4)
    since MySQL stores times in server local time (Gulf Standard Time).
    """
    if dt is None:
        return None
    if isinstance(dt, str):
        try:
            dt = datetime.strptime(dt, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            try:
                dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
            except ValueError:
                return dt
    
    if not isinstance(dt, datetime):
        return dt
    
    if dt.tzinfo is None:
        # Naive datetime from database - it's in DB server timezone (UTC+4)
        dt = dt.replace(tzinfo=DB_SERVER_TZ)
    
    # Convert to IST
    return dt.astimezone(IST)


def generate_roleplay_report(user_name, user_email, roleplay_name, scenario, 
                             overall_score, score_breakdown, interactions, 
                             completion_date=None, output_path=None):
    """
    Generate a comprehensive roleplay performance report with radar chart
    
    Args:
        user_name: Name of the user
        user_email: Email of the user
        roleplay_name: Name of the roleplay scenario
        scenario: Description of the roleplay scenario
        overall_score: Overall performance score (0-100)
        score_breakdown: List of dicts with {name, score, total_possible}
        interactions: List of interaction dicts with user_text, response_text, and score
        completion_date: Date of completion (defaults to now)
        output_path: Path to save the PDF (defaults to temp folder)
    
    Returns:
        Path to the generated PDF file
    """
    if completion_date is None:
        completion_date = get_ist_now()
    
    if output_path is None:
        from flask import current_app
        temp_dir = os.path.join(current_app.root_path, 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        timestamp = get_ist_now().strftime('%Y%m%d_%H%M%S')
        output_path = os.path.join(temp_dir, f'report_{user_email}_{timestamp}.pdf')
    
    # Create the PDF document
    doc = SimpleDocTemplate(output_path, pagesize=A4,
                           topMargin=0.5*inch, bottomMargin=0.5*inch,
                           leftMargin=0.75*inch, rightMargin=0.75*inch)
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=28,
        textColor=colors.black,
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.black,
        spaceAfter=12,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=8,
        alignment=TA_LEFT
    )
    
    score_style = ParagraphStyle(
        'ScoreStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#666666'),
        spaceAfter=4
    )
    
    # Title
    elements.append(Paragraph("FINAL REPORT", title_style))
    elements.append(Spacer(1, 0.3*inch))
    
    # SECTION 1: Radar Chart for Competencies
    # Include all items from score_breakdown
    print(f"DEBUG REPORT: score_breakdown = {score_breakdown}")
    
    # --- NEW LOGIC: Always include all enabled competencies from tags sheet ---
    # score_breakdown: list of {name, score, total_possible} for hit competencies
    # enabled_competencies: dict of {name: max_score} from tags sheet
    enabled_competencies = kwargs.get('enabled_competencies', {})
    # Build a lookup for score_breakdown
    score_lookup = {item.get('name', 'Unknown'): item for item in score_breakdown}

    competencies = {}
    score_totals_data = [['Name', 'Score', 'Total']]
    print(f"DEBUG REPORT: Building score totals table (all enabled competencies)")
    for comp_name, max_score in enabled_competencies.items():
        item = score_lookup.get(comp_name)
        score = item.get('score', 0) if item else 0
        total_possible = item.get('total_possible', max_score) if item else max_score
        percentage = (score / total_possible * 100) if total_possible > 0 else 0
        competencies[comp_name] = percentage
        score_totals_data.append([str(comp_name), str(score), str(total_possible)])
        print(f"DEBUG REPORT: {comp_name} = {score}/{total_possible}")

    print(f"DEBUG REPORT: competencies = {competencies}")

    if competencies:
        chart_image_path = generate_radar_chart(competencies)
        if chart_image_path and os.path.exists(chart_image_path):
            img = Image(chart_image_path, width=5.5*inch, height=4*inch)
            elements.append(img)
            elements.append(Spacer(1, 0.3*inch))

    elements.append(Paragraph("Score Totals", heading_style))
    score_table = Table(score_totals_data, colWidths=[3.5*inch, 1*inch, 1*inch])
    score_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f0f0')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.white])
    ]))
    elements.append(score_table)
    elements.append(Spacer(1, 0.4*inch))
    
    score_table = Table(score_totals_data, colWidths=[3.5*inch, 1*inch, 1*inch])
    score_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f0f0')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.white])
    ]))
    
    elements.append(score_table)
    elements.append(Spacer(1, 0.4*inch))
    
    # SECTION 3: Conversation Thread
    elements.append(Paragraph("Conversation Thread", heading_style))
    elements.append(Spacer(1, 0.2*inch))
    
    if interactions:
        for idx, interaction in enumerate(interactions, 1):
            # Get the score (star rating) for this interaction
            score_value = interaction.get('score', 0)
            # Use filled/empty star symbols
            stars = '★' * int(score_value) if score_value > 0 else ''
            
            # User message in green box - Use Paragraph for text wrapping
            user_text = interaction.get('user', '') or interaction.get('user_text', 'N/A')
            
            # Create a paragraph style for the table content with word wrapping
            user_paragraph = Paragraph(user_text, normal_style)
            
            user_data = [[user_paragraph]]
            user_table = Table(user_data, colWidths=[6*inch])
            user_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#d4edda')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ]))
            
            elements.append(user_table)
            
            # Score display - use simple text representation
            score_text = f"Score: {'★' * int(score_value)}" if score_value > 0 else "Score: -"
            elements.append(Paragraph(score_text, score_style))
            
            elements.append(Spacer(1, 0.15*inch))
    
    # Build PDF
    doc.build(elements)
    
    return output_path


def generate_radar_chart(competencies):
    """Generate a radar/polar chart for competencies"""
    try:
        # Prepare data
        categories = list(competencies.keys())
        values = [competencies[cat] for cat in categories]
        
        # Number of variables
        num_vars = len(categories)
        
        # Compute angle for each axis
        angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
        
        # Complete the circle
        values += values[:1]
        angles += angles[:1]
        
        # Create figure
        fig, ax = plt.subplots(figsize=(8, 6), subplot_kw=dict(projection='polar'))
        
        # Define colors for each competency
        colors_list = ['#87CEEB', '#90EE90', '#FFB6C1', '#FFE4B5', '#DDA0DD']
        
        # Plot data
        for i, (cat, val) in enumerate(competencies.items()):
            cat_angles = [angles[i], angles[i+1]]
            cat_values = [0, val, val, 0]
            cat_angles_fill = [angles[i], angles[i], angles[i+1], angles[i+1]]
            
            color = colors_list[i % len(colors_list)]
            ax.fill(cat_angles_fill, cat_values, color=color, alpha=0.6)
        
        # Fix axis to go from 0 to 100
        ax.set_ylim(0, 100)
        ax.set_yticks([20, 40, 60, 80])
        ax.set_yticklabels(['20', '40', '60', '80'])
        
        # Set category labels
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels([])  # Remove radial labels
        
        # Add legend
        ax.legend(categories, loc='upper left', bbox_to_anchor=(0.0, 1.15), fontsize=8, ncol=2)
        
        # Add grid
        ax.grid(True, linewidth=0.5, alpha=0.5)
        
        # Save to temporary file
        from flask import current_app
        temp_dir = os.path.join(current_app.root_path, 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        chart_path = os.path.join(temp_dir, f'chart_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png')
        
        plt.tight_layout()
        plt.savefig(chart_path, format='png', dpi=150, bbox_inches='tight')
        plt.close()
        
        return chart_path
        
    except Exception as e:
        print(f"Error generating radar chart: {e}")
        import traceback
        traceback.print_exc()
        return None


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
