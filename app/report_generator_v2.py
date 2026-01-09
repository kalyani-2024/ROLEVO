"""
Professional Report Generation Module for Rolevo - Skills Gauge Report
Generates comprehensive PDF reports matching the professional format with:
- Cover page with logos
- Activity summary with timer display
- Personality Fit analysis (placeholder for API integration)
- Competency Score by Cluster
- Competency Score by Activity
- Balance scale visualization for overused competencies
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether, BaseDocTemplate, Frame, PageTemplate, NextPageTemplate
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Circle, Polygon
from reportlab.graphics.charts.barcharts import HorizontalBarChart
from reportlab.graphics import renderPDF
from datetime import datetime, timezone, timedelta
import os
import matplotlib
matplotlib.use('Agg')
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
        # Attach the DB server timezone, then convert to IST
        dt = dt.replace(tzinfo=DB_SERVER_TZ)
    
    # Convert to IST
    return dt.astimezone(IST)

# Color constants matching the design
GREEN_PRIMARY = colors.HexColor('#1E7D32')  # Dark green for headers
GREEN_LIGHT = colors.HexColor('#4CAF50')    # Light green
YELLOW_PRIMARY = colors.HexColor('#FFC107') # Yellow for personality section
RED_WARNING = colors.HexColor('#DC3545')    # Red for overused
GRAY_HEADER = colors.HexColor('#6B7280')    # Gray for table headers
WHITE = colors.white
BLACK = colors.black

# 16PF Trait Mapping - Maps API factor names to display format with left/right traits
PF16_TRAIT_MAPPING = {
    'Warmth': {
        'code': 'A', 'left_name': 'A: Cool', 'left_desc': 'reserved, impersonal, detached formal, aloof',
        'right_name': 'A: Warm', 'right_desc': 'Outgoing, Kindly, Easy going, Participating, Likes people'
    },
    'Reasoning': {
        'code': 'B', 'left_name': 'B: Concrete', 'left_desc': 'thinking, less intelligent',
        'right_name': 'B: Abstract', 'right_desc': 'thinking, more intelligent and bright'
    },
    'Emotional Stability': {
        'code': 'C', 'left_name': 'C: Affected by feelings', 'left_desc': 'emotionally less stable, easily annoyed',
        'right_name': 'C: Emotionally stable', 'right_desc': 'mature, calm, realistic'
    },
    'Dominance': {
        'code': 'E', 'left_name': 'E: Submissive', 'left_desc': 'humble, accommodating, mild, easily led',
        'right_name': 'E: Dominant', 'right_desc': 'assertive, aggressive, competitive, self-assured, authoritative and stubborn'
    },
    'Liveliness': {
        'code': 'F', 'left_name': 'F: Sober', 'left_desc': 'Restrained, prudent, taciturn, serious, introspective and pessimistic',
        'right_name': 'F: Enthusiastic', 'right_desc': 'spontaneous, expressive, cheerful, talkative, carefree'
    },
    'Rule-Consciousness': {
        'code': 'G', 'left_name': 'G: Expedient', 'left_desc': 'disregards rules, self-indulgent',
        'right_name': 'G: Rule-Conscious', 'right_desc': 'dutiful, conscientious, conforming, moralistic'
    },
    'Social Boldness': {
        'code': 'H', 'left_name': 'H: Shy', 'left_desc': 'threat-sensitive, timid, hesitant',
        'right_name': 'H: Bold', 'right_desc': 'socially bold, venturesome, thick-skinned'
    },
    'Sensitivity': {
        'code': 'I', 'left_name': 'I: Tough-Minded', 'left_desc': 'utilitarian, objective, unsentimental',
        'right_name': 'I: Sensitive', 'right_desc': 'aesthetic, sentimental, tender-minded'
    },
    'Vigilance': {
        'code': 'L', 'left_name': 'L: Trusting', 'left_desc': 'accepting conditions, easy to get on with',
        'right_name': 'L: Vigilant', 'right_desc': 'suspicious, skeptical, distrustful, oppositional'
    },
    'Abstractedness': {
        'code': 'M', 'left_name': 'M: Practical', 'left_desc': 'grounded, down-to-earth, prosaic',
        'right_name': 'M: Abstracted', 'right_desc': 'imaginative, idea-oriented, absorbed in ideas'
    },
    'Privateness': {
        'code': 'N', 'left_name': 'N: Forthright', 'left_desc': 'genuine, artless, open, unpretentious',
        'right_name': 'N: Private', 'right_desc': 'discreet, non-disclosing, shrewd, polished'
    },
    'Apprehension': {
        'code': 'O', 'left_name': 'O: Self-Assured', 'left_desc': 'unworried, complacent, secure, self-satisfied',
        'right_name': 'O: Apprehensive', 'right_desc': 'self-doubting, worried, guilt-prone, insecure'
    },
    'Openness to Change': {
        'code': 'Q1', 'left_name': 'Q1: Traditional', 'left_desc': 'attached to familiar, conservative',
        'right_name': 'Q1: Open to Change', 'right_desc': 'experimenting, liberal, critical, freethinking'
    },
    'Self-Reliance': {
        'code': 'Q2', 'left_name': 'Q2: Group-Oriented', 'left_desc': 'affiliative, a joiner and follower',
        'right_name': 'Q2: Self-Reliant', 'right_desc': 'solitary, resourceful, individualistic'
    },
    'Perfectionism': {
        'code': 'Q3', 'left_name': 'Q3: Tolerates Disorder', 'left_desc': 'flexible, undisciplined, impulsive',
        'right_name': 'Q3: Perfectionistic', 'right_desc': 'organized, compulsive, self-disciplined'
    },
    'Tension': {
        'code': 'Q4', 'left_name': 'Q4: Relaxed', 'left_desc': 'patient, composed, low drive',
        'right_name': 'Q4: Tense', 'right_desc': 'driven, impatient, high energy, time-driven'
    },
}

def convert_personality_data_to_16pf_format(personality_scores):
    """Convert simple personality scores dict to full 16PF display format.
    
    Args:
        personality_scores: Dict of {'Warmth': 6, 'Reasoning': 7, ...}
        
    Returns:
        List of dicts with left_name, left_desc, right_name, right_desc, score, target
    """
    result = []
    
    for trait_name, mapping in PF16_TRAIT_MAPPING.items():
        score = personality_scores.get(trait_name, 5)  # Default to 5 if not found
        result.append({
            'left_name': mapping['left_name'],
            'left_desc': mapping['left_desc'],
            'right_name': mapping['right_name'],
            'right_desc': mapping['right_desc'],
            'score': score,
            'target': 5  # Neutral target
        })
    
    return result


class SkillsGaugeReport:
    """Professional Skills Gauge Report Generator"""
    
    def __init__(self, output_path=None):
        self.output_path = output_path
        self.page_width, self.page_height = A4
        self.margin = 0.5 * inch
        self.styles = self._create_styles()
        
    def _create_styles(self):
        """Create custom paragraph styles"""
        styles = getSampleStyleSheet()
        
        styles.add(ParagraphStyle(
            'ReportTitle',
            parent=styles['Heading1'],
            fontSize=32,
            textColor=GREEN_PRIMARY,
            alignment=TA_CENTER,
            spaceAfter=20,
            fontName='Helvetica-Bold'
        ))
        
        styles.add(ParagraphStyle(
            'SectionHeader',
            parent=styles['Heading2'],
            fontSize=24,
            textColor=WHITE,
            alignment=TA_CENTER,
            spaceAfter=15,
            fontName='Helvetica-Bold'
        ))
        
        styles.add(ParagraphStyle(
            'SubHeader',
            parent=styles['Heading3'],
            fontSize=16,
            textColor=GREEN_PRIMARY,
            alignment=TA_CENTER,
            spaceAfter=10,
            fontName='Helvetica-Bold'
        ))
        
        styles.add(ParagraphStyle(
            'NormalCenter',
            parent=styles['Normal'],
            fontSize=11,
            alignment=TA_CENTER
        ))
        
        styles.add(ParagraphStyle(
            'NormalRight',
            parent=styles['Normal'],
            fontSize=11,
            alignment=TA_RIGHT
        ))
        
        styles.add(ParagraphStyle(
            'CompetencyName',
            parent=styles['Normal'],
            fontSize=10,
            fontName='Helvetica-Bold',
            textColor=GREEN_PRIMARY
        ))
        
        styles.add(ParagraphStyle(
            'CompetencyDesc',
            parent=styles['Normal'],
            fontSize=7,
            textColor=colors.HexColor('#666666'),
            leading=9
        ))
        
        return styles
    
    def _create_header_banner(self, title, bg_color=GREEN_PRIMARY, height=60):
        """Create a colored banner for section headers"""
        # Create a table that spans full width with colored background
        banner_data = [[Paragraph(f'<font color="white">{title}</font>', 
                                   ParagraphStyle('BannerText', 
                                                 fontSize=22, 
                                                 alignment=TA_CENTER,
                                                 textColor=WHITE,
                                                 fontName='Helvetica-Bold'))]]
        
        banner = Table(banner_data, colWidths=[self.page_width - 2*self.margin])
        banner.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), bg_color),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 15),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
        ]))
        
        return banner
    
    def _create_logo_header(self, trajectorie_logo_path=None, client_logo_path=None):
        """Create header with both logos"""
        elements = []
        
        # Logo paths
        if not trajectorie_logo_path:
            from flask import current_app
            trajectorie_logo_path = os.path.join(current_app.root_path, 'static', 'images', 'logo-trajectorie-codrive.png')
        
        # Create header table with logos on both sides
        logo_data = []
        
        # Left side: Client logo or placeholder
        if client_logo_path and os.path.exists(client_logo_path):
            left_logo = Image(client_logo_path, width=1.5*inch, height=0.6*inch)
        else:
            left_logo = Paragraph('<font color="#888888">CLIENT LOGO</font>', 
                                  ParagraphStyle('ClientLogo', fontSize=10, alignment=TA_LEFT))
        
        # Right side: Trajectorie logo
        if trajectorie_logo_path and os.path.exists(trajectorie_logo_path):
            right_logo = Image(trajectorie_logo_path, width=1.5*inch, height=0.5*inch)
        else:
            right_logo = Paragraph('<font color="#1E7D32">Trajectorie</font>', 
                                   ParagraphStyle('TrajLogo', fontSize=12, alignment=TA_RIGHT))
        
        logo_data.append([left_logo, '', right_logo])
        
        logo_table = Table(logo_data, colWidths=[2*inch, 3*inch, 2*inch])
        logo_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        return logo_table
    
    def _create_score_bar(self, score, target_score=60, width=200, height=15):
        """Create a horizontal score bar with gradient coloring"""
        # Determine bar color based on score
        if score >= 80:
            bar_color = colors.HexColor('#28A745')  # Green
        elif score >= 60:
            bar_color = colors.HexColor('#FFC107')  # Yellow
        elif score >= 40:
            bar_color = colors.HexColor('#FF9800')  # Orange
        else:
            bar_color = colors.HexColor('#DC3545')  # Red
        
        # Create drawing
        d = Drawing(width + 60, height + 10)
        
        # Background bar (gray)
        d.add(Rect(0, 2, width, height, fillColor=colors.HexColor('#E5E5E5'), strokeColor=None))
        
        # Score bar
        bar_width = min(score / 100 * width, width)
        d.add(Rect(0, 2, bar_width, height, fillColor=bar_color, strokeColor=None))
        
        # Column markers for Significant, Needs Improvement, Average, Good, Proficient
        # These are at 20%, 40%, 60%, 80%, 100%
        for pct in [20, 40, 60, 80]:
            x = pct / 100 * width
            d.add(Line(x, 0, x, height + 4, strokeColor=colors.white, strokeWidth=1))
        
        # User score marker (filled circle)
        score_x = min(score / 100 * width, width)
        d.add(Circle(score_x, height/2 + 2, 5, fillColor=GREEN_PRIMARY, strokeColor=WHITE, strokeWidth=1.5))
        
        return d
    
    def _create_competency_table(self, competencies, title="Competency Scores"):
        """Create a formatted competency score table with gradient progress bars"""
        elements = []
        
        # Column headers
        header_style = ParagraphStyle('TableHeader', fontSize=8, alignment=TA_CENTER,
                                      textColor=GRAY_HEADER, fontName='Helvetica-Bold')
        
        headers = [
            Paragraph('', header_style),  # Competency name
            Paragraph('%', header_style),
            Paragraph('Significant<br/>Shortcoming', header_style),
            Paragraph('Needs<br/>Improvement', header_style),
            Paragraph('Average', header_style),
            Paragraph('Good', header_style),
            Paragraph('Proficient', header_style)
        ]
        
        table_data = [headers]
        
        for comp in competencies:
            name = comp.get('name', 'Unknown')
            description = comp.get('description', '')
            score = comp.get('score', 0)
            target = comp.get('target', 60)
            
            # Create competency cell with name and description
            if description:
                comp_text = f'<font size="9"><b>{name}</b></font><br/><font size="7" color="#666666"><i>{description[:80]}...</i></font>' if len(description) > 80 else f'<font size="9"><b>{name}</b></font><br/><font size="7" color="#666666"><i>{description}</i></font>'
            else:
                comp_text = f'<font size="9"><b>{name}</b></font>'
            
            comp_para = Paragraph(comp_text, self.styles['Normal'])
            
            # Score percentage
            score_para = Paragraph(f'<font size="10"><b>{int(score)}%</b></font>',
                                   ParagraphStyle('ScorePct', alignment=TA_CENTER))
            
            # Create gradient bar cells - we'll use colored backgrounds
            # Determine which column the score falls into
            # 0-20: Significant Shortcoming, 20-40: Needs Improvement, 40-60: Average, 60-80: Good, 80-100: Proficient
            
            # Create the score bar as a drawing that spans multiple columns
            bar_drawing = self._create_score_bar(score, target, width=280, height=12)
            
            row = [comp_para, score_para, bar_drawing, '', '', '', '']
            table_data.append(row)
        
        # Create table with score bar spanning columns 2-6
        col_widths = [2.2*inch, 0.5*inch, 0.7*inch, 0.7*inch, 0.65*inch, 0.55*inch, 0.7*inch]
        table = Table(table_data, colWidths=col_widths)
        
        # Create style with spans for score bars
        style_commands = [
            # Header styling
            ('BACKGROUND', (2, 0), (-1, 0), colors.HexColor('#F0F0F0')),
            ('TEXTCOLOR', (0, 0), (-1, 0), GRAY_HEADER),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#DDDDDD')),
            # Header bottom border
            ('LINEBELOW', (0, 0), (-1, 0), 1.5, colors.HexColor('#999999')),
            # Row backgrounds
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, colors.HexColor('#FAFAFA')]),
            # Padding
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ]
        
        # Add spans for the score bars (row 1 onwards, columns 2-6)
        for i in range(1, len(table_data)):
            style_commands.append(('SPAN', (2, i), (6, i)))
        
        table.setStyle(TableStyle(style_commands))
        
        return table
    
    def _create_balance_scale_image(self, overused_competencies):
        """Create balance scale visualization with overused competencies.
        Only displays if there is at least one overused competency.
        Each competency shown as a red box with name and score like 'Feedback (Basic) 5/3'
        """
        from flask import current_app
        
        elements = []
        
        # Only show this section if there are overused competencies
        if not overused_competencies or len(overused_competencies) == 0:
            return elements
        
        # Balance scale image - try both possible filenames
        balance_img_path = os.path.join(current_app.root_path, 'static', 'images', 'balancescale.png')
        if not os.path.exists(balance_img_path):
            balance_img_path = os.path.join(current_app.root_path, 'static', 'images', 'balance_scale.png')
        
        if os.path.exists(balance_img_path):
            # Create a table with image and title side by side
            img = Image(balance_img_path, width=2.5*inch, height=1.8*inch)
            title_para = Paragraph('<font color="#1E7D32"><b>Competencies likely<br/>to be overused</b></font>',
                                   ParagraphStyle('BalanceTitle', fontSize=14, alignment=TA_LEFT,
                                                 textColor=GREEN_PRIMARY, leading=18))
            
            balance_table = Table([[img, title_para]], colWidths=[2.8*inch, 3*inch])
            balance_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (1, 0), (1, 0), 'LEFT'),
            ]))
            elements.append(balance_table)
        else:
            # Fallback title if image doesn't exist
            elements.append(Paragraph('<font color="#1E7D32"><b>Competencies likely to be overused</b></font>', 
                                     self.styles['SubHeader']))
        
        elements.append(Spacer(1, 0.2*inch))
        
        # Create red boxes for overused competencies in tile format
        # Each box shows: name on top, score (e.g., "5/3") below
        red_boxes = []
        for comp in overused_competencies:
            name = comp.get('name', 'Unknown')
            score = comp.get('score', 0)
            max_score = comp.get('max_score', 3)
            
            # Create a styled red box with name and score
            red_boxes.append(self._create_overused_box(name, score, max_score))
        
        # Arrange boxes in rows (max 4 per row for better fit)
        boxes_per_row = 4
        total_width = self.page_width - 2*self.margin
        box_width = 1.5*inch
        
        row_data = []
        current_row = []
        for box in red_boxes:
            current_row.append(box)
            if len(current_row) >= boxes_per_row:
                row_data.append(current_row)
                current_row = []
        
        # Add remaining boxes in the last row
        if current_row:
            # Pad with empty cells
            while len(current_row) < boxes_per_row:
                current_row.append('')
            row_data.append(current_row)
        
        if row_data:
            # Calculate column widths - evenly spaced
            col_widths = [box_width] * boxes_per_row
            
            box_table = Table(row_data, colWidths=col_widths, rowHeights=[0.75*inch] * len(row_data))
            box_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 3),
                ('RIGHTPADDING', (0, 0), (-1, -1), 3),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            elements.append(box_table)
        
        return elements
    
    def _create_overused_box(self, name, score, max_score):
        """Create a single red box for an overused competency.
        Format: Name on top, Score/Max below (like 'Feedback (Basic)' and '5/3')
        """
        # Style for the name (smaller, white)
        name_style = ParagraphStyle('OverusedName', fontSize=8, fontName='Helvetica-Bold',
                                   textColor=WHITE, alignment=TA_CENTER, leading=10)
        # Style for the score (larger, white, bold)
        score_style = ParagraphStyle('OverusedScore', fontSize=14, fontName='Helvetica-Bold',
                                    textColor=WHITE, alignment=TA_CENTER)
        
        # Create the inner content
        name_para = Paragraph(name, name_style)
        score_para = Paragraph(f'{score}/{max_score}', score_style)
        
        # Create inner table for layout
        inner_table = Table([
            [name_para],
            [score_para]
        ], colWidths=[1.4*inch], rowHeights=[0.25*inch, 0.35*inch])
        
        inner_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#DC3545')),  # Red background
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ]))
        
        return inner_table
    
    def generate_cover_page(self, user_name, report_date=None, client_logo_path=None, cover_image_path=None):
        """Generate the cover page - returns PageBreak only, actual drawing is done in canvas callback"""
        # The cover page content is drawn directly on canvas in the page template callback
        # This method just returns a PageBreak to move to the next page
        return [PageBreak()]
    
    def draw_cover_page(self, canvas, doc, user_name, report_date, cover_image_path=None, client_logo_path=None):
        """Draw the cover page directly on canvas - called from page template"""
        from flask import current_app
        
        # Get cover image path
        if cover_image_path is None:
            cover_image_path = os.path.join(current_app.root_path, 'static', 'images', 'report_cover_collage.png')
        
        # Get Trajectorie logo path
        traj_logo_path = os.path.join(current_app.root_path, 'static', 'images', 'logo-trajectorie-codrive.png')
        
        if report_date is None:
            report_date = get_ist_now()
        else:
            # Convert to IST if provided
            report_date = convert_to_ist(report_date) or get_ist_now()
        
        page_width, page_height = A4
        
        # Draw full-page background image
        if os.path.exists(cover_image_path):
            canvas.drawImage(
                cover_image_path,
                0,  # x = left edge
                0,  # y = bottom edge
                width=page_width,
                height=page_height,
                preserveAspectRatio=False,
                mask='auto'
            )
        
        # === HEADER WITH LOGOS ===
        header_y = page_height - 0.8 * inch  # Top of page minus margin
        
        # Client logo - top left (placeholder if not provided)
        if client_logo_path and os.path.exists(client_logo_path):
            canvas.drawImage(
                client_logo_path,
                0.5 * inch,
                header_y - 0.3 * inch,
                width=1.2 * inch,
                height=0.5 * inch,
                preserveAspectRatio=True,
                mask='auto'
            )
        else:
            # Draw placeholder box with "CLIENT LOGO" text
            canvas.setFillColor(colors.HexColor('#E0E0E0'))
            canvas.rect(0.5 * inch, header_y - 0.3 * inch, 1.2 * inch, 0.4 * inch, fill=True, stroke=False)
            canvas.setFillColor(colors.HexColor('#666666'))
            canvas.setFont('Helvetica', 8)
            canvas.drawCentredString(0.5 * inch + 0.6 * inch, header_y - 0.15 * inch, 'CLIENT LOGO')
        
        # Trajectorie logo - top right
        if os.path.exists(traj_logo_path):
            canvas.drawImage(
                traj_logo_path,
                page_width - 0.5 * inch - 1.8 * inch,
                header_y - 0.4 * inch,
                width=1.8 * inch,
                height=0.6 * inch,
                preserveAspectRatio=True,
                mask='auto'
            )
        else:
            # Fallback text if logo not found
            canvas.setFillColor(GREEN_PRIMARY)
            canvas.setFont('Helvetica-Bold', 14)
            canvas.drawRightString(page_width - 0.5 * inch, header_y - 0.1 * inch, 'Trajectorie')
        
        # === FOOTER ===
        # Draw semi-transparent footer bar for better text visibility
        footer_bar_height = 0.8 * inch
        canvas.setFillColor(colors.Color(0, 0, 0, alpha=0.5))  # Semi-transparent black
        canvas.rect(0, 0, page_width, footer_bar_height, fill=True, stroke=False)
        
        # Draw footer content at the bottom of page
        footer_y = 0.35 * inch  # Position within footer bar
        
        # Company name - bottom left (white text)
        canvas.setFont('Helvetica-Bold', 10)
        canvas.setFillColor(WHITE)
        canvas.drawString(0.5 * inch, footer_y, 'Trajectories Business Solutions Pvt. Ltd.')
        
        # Report info - bottom right (white text)
        report_info = f"Report For: {user_name}"
        date_info = f"Report Date: {report_date.strftime('%d/%m/%Y | %I:%M:%S %p')} IST"
        
        canvas.setFont('Helvetica', 10)
        right_x = page_width - 0.5 * inch
        canvas.drawRightString(right_x, footer_y + 14, report_info)
        canvas.drawRightString(right_x, footer_y, date_info)
    
    def generate_activity_summary_page(self, activities, total_time_available=None, 
                                       total_time_taken=None, client_logo_path=None):
        """Generate the Activity Summary page matching the professional design"""
        elements = []
        from flask import current_app
        
        # Header with logos
        traj_logo = os.path.join(current_app.root_path, 'static', 'images', 'logo-trajectorie-codrive.png')
        elements.append(self._create_logo_header(traj_logo, client_logo_path))
        elements.append(Spacer(1, 0.3*inch))
        
        # Activity Summary banner - use pre-made image
        activity_summary_img = os.path.join(current_app.root_path, 'static', 'images', 'activity summary.png')
        
        if os.path.exists(activity_summary_img):
            # Use the pre-made activity summary banner image with proper aspect ratio
            # Original image is 738x152, aspect ratio ~4.86
            banner_width = self.page_width - 2*self.margin
            banner_height = banner_width / 4.86  # Maintain aspect ratio
            banner_img = Image(activity_summary_img, width=banner_width, height=banner_height)
            elements.append(banner_img)
        else:
            # Fallback to text banner if image not found
            banner_style = ParagraphStyle('BannerStyle', fontSize=24, alignment=TA_CENTER,
                                          textColor=WHITE, fontName='Helvetica-Bold')
            banner_content = Paragraph('Activity Summary', banner_style)
            
            banner = Table([[banner_content]], colWidths=[self.page_width - 2*self.margin])
            banner.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), GREEN_PRIMARY),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 12),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ]))
            elements.append(banner)
        elements.append(Spacer(1, 0.5*inch))
        
        # Timer section with timer.png image
        timer_img_path = os.path.join(current_app.root_path, 'static', 'images', 'timer.png')
        
        # Time info on right side
        time_style = ParagraphStyle('TimeStyle', fontSize=14, alignment=TA_LEFT, leading=28)
        time_text = f'''<font color="#1E7D32"><b>Time available: {total_time_available or "5Hr : 50Min"}</b></font><br/>
<font color="#1E7D32"><b>Time taken:&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; {total_time_taken or "0Hr : 0Min"}</b></font>'''
        time_para = Paragraph(time_text, time_style)
        
        if os.path.exists(timer_img_path):
            timer_img = Image(timer_img_path, width=2.8*inch, height=1.2*inch)
            timer_table = Table([[timer_img, time_para]], colWidths=[3.2*inch, 3.8*inch])
        else:
            # Placeholder timer display if timer.png not found
            timer_placeholder = Table([['05:41:09']], colWidths=[2.5*inch], rowHeights=[1*inch])
            timer_placeholder.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#333333')),
                ('TEXTCOLOR', (0, 0), (-1, -1), WHITE),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTSIZE', (0, 0), (-1, -1), 28),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ]))
            timer_table = Table([[timer_placeholder, time_para]], colWidths=[3.2*inch, 3.8*inch])
        
        timer_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (0, 0), 'CENTER'),
            ('ALIGN', (1, 0), (1, 0), 'LEFT'),
            ('LEFTPADDING', (1, 0), (1, 0), 20),
        ]))
        elements.append(timer_table)
        elements.append(Spacer(1, 0.5*inch))
        
        # Skills Gauge Activities header
        elements.append(Paragraph('<font color="#1E7D32"><b>Skills Gauge Activities</b></font>',
                                  ParagraphStyle('ActivitiesHeader', fontSize=20, alignment=TA_CENTER,
                                                fontName='Helvetica-Bold', spaceAfter=20)))
        
        # Decorative line under title
        line_table = Table([['']], colWidths=[3*inch], rowHeights=[3])
        line_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), GREEN_PRIMARY),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        centered_line = Table([[line_table]], colWidths=[self.page_width - 2*self.margin])
        centered_line.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
        elements.append(centered_line)
        elements.append(Spacer(1, 0.4*inch))
        
        # Activity cards - 2 activities: 16PF Trait Assessment and Critical Conversations (AI)
        # Default activities with correct icons
        default_activities = [
            {'name': '16PF Trait\nAssessment', 'icon': 'meeting.png', 
             'time_available': '1Hr : 39Min', 'time_taken': '0Hr : 0Min'},
            {'name': 'Critical\nConversations (AI)', 'icon': 'live-chat.png',
             'time_available': '1Hr : 39Min', 'time_taken': '0Hr : 0Min'},
        ]
        
        # Merge provided activities with defaults
        if activities:
            for i, act in enumerate(activities):
                if i < len(default_activities):
                    default_activities[i].update(act)
        
        # Create activity cards
        activity_rows = []
        row = []
        
        for activity in default_activities:
            name = activity.get('name', 'Activity')
            time_avail = activity.get('time_available', '0Hr : 0Min')
            time_taken = activity.get('time_taken', '0Hr : 0Min')
            icon_file = activity.get('icon', '')
            
            # Check for icon
            icon_path = os.path.join(current_app.root_path, 'static', 'images', icon_file)
            
            # Icon placeholder (gray box with simple shape)
            icon_placeholder = Table([['📊']], colWidths=[0.6*inch], rowHeights=[0.6*inch])
            icon_placeholder.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F0F0F0')),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTSIZE', (0, 0), (-1, -1), 20),
            ]))
            
            if os.path.exists(icon_path):
                icon_elem = Image(icon_path, width=0.6*inch, height=0.6*inch)
            else:
                icon_elem = icon_placeholder
            
            # Activity text with green for time available, red for time taken
            activity_text = f'''<font size="11" color="#1E7D32"><b>{name}</b></font><br/><br/>
<font size="9" color="#1E7D32"><b>Time available:</b> {time_avail}</font><br/>
<font size="9" color="#DC3545"><b>Time taken:</b>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; {time_taken}</font>'''
            activity_para = Paragraph(activity_text, self.styles['Normal'])
            
            # Card layout: icon on left, text on right
            card_content = Table([[icon_elem, activity_para]], colWidths=[0.8*inch, 2.2*inch])
            card_content.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (1, 0), (1, 0), 10),
            ]))
            
            row.append(card_content)
            
            if len(row) >= 2:
                activity_rows.append(row)
                row = []
        
        if row:
            while len(row) < 2:
                row.append('')
            activity_rows.append(row)
        
        if activity_rows:
            activities_table = Table(activity_rows, colWidths=[3.4*inch, 3.4*inch])
            activities_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8F9FA')),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#E0E0E0')),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E0E0E0')),
                ('TOPPADDING', (0, 0), (-1, -1), 15),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            elements.append(activities_table)
        
        elements.append(PageBreak())
        return elements
    
    def generate_personality_fit_page(self, personality_data=None, overall_role_fit=None,
                                      client_logo_path=None):
        """Generate the Personality Fit (Voice) page - 16PF Voice Analysis"""
        elements = []
        from flask import current_app
        
        # Header with logos
        traj_logo = os.path.join(current_app.root_path, 'static', 'images', 'logo-trajectorie-codrive.png')
        elements.append(self._create_logo_header(traj_logo, client_logo_path))
        elements.append(Spacer(1, 0.3*inch))
        
        # Personality Fit banner - use pre-made image
        personality_fit_img = os.path.join(current_app.root_path, 'static', 'images', 'personality fit.png')
        
        if os.path.exists(personality_fit_img):
            # Use the pre-made personality fit banner image with proper aspect ratio
            banner_width = self.page_width - 2*self.margin
            banner_height = banner_width / 4.82  # Maintain aspect ratio (738x153)
            banner_img = Image(personality_fit_img, width=banner_width, height=banner_height)
            elements.append(banner_img)
        else:
            # Fallback to text banner if image not found
            elements.append(self._create_header_banner('Personality Fit (Voice)', YELLOW_PRIMARY))
        elements.append(Spacer(1, 0.4*inch))
        
        # 16 PF Trait Assessment section with avatar and info
        pf16_logo = os.path.join(current_app.root_path, 'static', 'images', '16pf logo.png')
        
        # Create avatar/logo - larger to span down to Attempted Questions
        logo_size = 1.1*inch
        if os.path.exists(pf16_logo):
            avatar_img = Image(pf16_logo, width=logo_size, height=logo_size)
        else:
            avatar_placeholder = Table([['👤']], colWidths=[logo_size], rowHeights=[logo_size])
            avatar_placeholder.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#E0E0E0')),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTSIZE', (0, 0), (-1, -1), 24),
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CCCCCC')),
            ]))
            avatar_img = avatar_placeholder
        
        # 16 PF Trait Assessment title and info
        # Calculate widths based on page
        total_width = self.page_width - 2*self.margin
        logo_width = 1.15*inch
        title_area_width = total_width - logo_width - 0.1*inch
        
        # Title bar spans full page width for center alignment
        title_style = ParagraphStyle('PFTitle', fontSize=14, fontName='Helvetica-Bold',
                                     textColor=WHITE, alignment=TA_CENTER)
        title_bar = Table([[Paragraph('16 PF Trait Assessment', title_style)]],
                         colWidths=[total_width])
        title_bar.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), GREEN_PRIMARY),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        
        # Info text - properly aligned columns
        info_label_style = ParagraphStyle('InfoLabel', fontSize=10, fontName='Helvetica-Bold', leading=16)
        info_val_style = ParagraphStyle('InfoVal', fontSize=10, leading=16)
        
        # Create a 4-column table for proper alignment
        info_table = Table([
            [Paragraph('Total Questions', info_label_style), 
             Paragraph('- 2', info_val_style),
             Paragraph('Time available', info_label_style), 
             Paragraph('- 1Hr : 39Min', info_val_style)],
            [Paragraph('Attempted Questions', info_label_style), 
             Paragraph('- 2', info_val_style),
             Paragraph('Time taken', info_label_style), 
             Paragraph('- 0Hr : 41Min', info_val_style)],
        ], colWidths=[1.5*inch, 0.4*inch, 1.2*inch, 1.2*inch])
        info_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        
        # Add title bar first (full width, center aligned with page)
        elements.append(title_bar)
        elements.append(Spacer(1, 0.1*inch))
        
        # Logo and info section side by side
        logo_col_width = 1.15*inch
        info_col_width = total_width - logo_col_width
        
        header_content = Table([[avatar_img, info_table]], colWidths=[logo_col_width, info_col_width])
        header_content.setStyle(TableStyle([
            ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),  # Logo vertically centered
            ('VALIGN', (1, 0), (1, 0), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (0, 0), 0),
            ('LEFTPADDING', (1, 0), (1, 0), 15),
        ]))
        
        elements.append(header_content)
        elements.append(Spacer(1, 0.2*inch))
        
        # Score table with 16PF traits - complete data with left/right descriptors
        # If no personality data passed, skip the score table (don't use fake data)
        if not personality_data:
            # Show message that 16PF analysis is not available
            no_data_style = ParagraphStyle('NoData', fontSize=12, alignment=TA_CENTER,
                                           textColor=colors.HexColor('#666666'), spaceAfter=20)
            elements.append(Spacer(1, 0.5*inch))
            elements.append(Paragraph('<i>16PF Voice Analysis data not available.</i>', no_data_style))
            elements.append(Paragraph('<i>The voice analysis API may be unavailable or the analysis is still pending.</i>', no_data_style))
            elements.append(Spacer(1, 0.3*inch))
        else:
            # Check if data is in simple format (name, score) vs full format (left_name, right_name)
            if isinstance(personality_data, list) and len(personality_data) > 0:
                first_item = personality_data[0]
                if 'left_name' not in first_item and 'name' in first_item:
                    # Convert simple format to full 16PF format
                    scores_dict = {item.get('name'): item.get('score', 5) for item in personality_data}
                    personality_data = convert_personality_data_to_16pf_format(scores_dict)
            
            # Create score table - fits on one page
            elements.extend(self._create_16pf_score_table(personality_data))
        
        elements.append(PageBreak())
        
        # Add 16PF reference table page (Low Score / High Score)
        elements.extend(self._create_16pf_reference_table())
        
        elements.append(PageBreak())
        return elements
    
    def _create_16pf_activity_score_page1(self, personality_data):
        """Create the 16PF Activity Score page 1 (Factors A through I) - Competency Score by Activity"""
        elements = []
        from flask import current_app
        
        total_width = self.page_width - 2*self.margin
        
        # Header with logos
        traj_logo = os.path.join(current_app.root_path, 'static', 'images', 'logo-trajectorie-codrive.png')
        # Get client logo if available (passed via context)
        elements.append(self._create_logo_header(traj_logo, None))
        elements.append(Spacer(1, 0.2*inch))
        
        # Personality Fit banner
        personality_fit_img = os.path.join(current_app.root_path, 'static', 'images', 'personality fit.png')
        if os.path.exists(personality_fit_img):
            banner_width = total_width
            banner_height = banner_width / 4.82
            banner_img = Image(personality_fit_img, width=banner_width, height=banner_height)
            elements.append(banner_img)
        elements.append(Spacer(1, 0.2*inch))
        
        # Title section with avatar
        pf16_logo = os.path.join(current_app.root_path, 'static', 'images', '16pf logo.png')
        logo_size = 0.8*inch
        
        if os.path.exists(pf16_logo):
            avatar_img = Image(pf16_logo, width=logo_size, height=logo_size)
        else:
            avatar_placeholder = Table([['👤']], colWidths=[logo_size], rowHeights=[logo_size])
            avatar_placeholder.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#E0E0E0')),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CCCCCC')),
            ]))
            avatar_img = avatar_placeholder
        
        # Title
        title_style = ParagraphStyle('ActivityTitle', fontSize=12, fontName='Helvetica-Bold',
                                     textColor=WHITE, alignment=TA_CENTER)
        title_bar = Table([[Paragraph('16 PF Trait Assessment - Details', title_style)]],
                         colWidths=[total_width - logo_size - 0.15*inch])
        title_bar.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), GREEN_PRIMARY),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        # Combine avatar and title
        header_table = Table([[avatar_img, title_bar]], 
                           colWidths=[logo_size + 0.05*inch, total_width - logo_size - 0.05*inch])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Descriptors header
        desc_style = ParagraphStyle('DescHeader', fontSize=11, fontName='Helvetica-Bold',
                                   textColor=WHITE, alignment=TA_CENTER)
        desc_bar = Table([[Paragraph('Descriptors: 16 Personality Factors (PF)', desc_style)]],
                        colWidths=[total_width])
        desc_bar.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), GREEN_PRIMARY),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(desc_bar)
        elements.append(Spacer(1, 0.1*inch))
        
        # Create the scores table
        elements.append(self._create_16pf_activity_table(personality_data, page=1))
        
        return elements
    
    def _create_16pf_activity_score_page2(self, personality_data):
        """Create the 16PF Activity Score page 2 (Factors L through Q4) - Competency Score by Activity"""
        elements = []
        from flask import current_app
        
        total_width = self.page_width - 2*self.margin
        
        # Header with logos
        traj_logo = os.path.join(current_app.root_path, 'static', 'images', 'logo-trajectorie-codrive.png')
        elements.append(self._create_logo_header(traj_logo, None))
        elements.append(Spacer(1, 0.2*inch))
        
        # Personality Fit banner
        personality_fit_img = os.path.join(current_app.root_path, 'static', 'images', 'personality fit.png')
        if os.path.exists(personality_fit_img):
            banner_width = total_width
            banner_height = banner_width / 4.82
            banner_img = Image(personality_fit_img, width=banner_width, height=banner_height)
            elements.append(banner_img)
        elements.append(Spacer(1, 0.2*inch))
        
        # Title section with avatar
        pf16_logo = os.path.join(current_app.root_path, 'static', 'images', '16pf logo.png')
        logo_size = 0.8*inch
        
        if os.path.exists(pf16_logo):
            avatar_img = Image(pf16_logo, width=logo_size, height=logo_size)
        else:
            avatar_placeholder = Table([['👤']], colWidths=[logo_size], rowHeights=[logo_size])
            avatar_placeholder.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#E0E0E0')),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CCCCCC')),
            ]))
            avatar_img = avatar_placeholder
        
        # Title
        title_style = ParagraphStyle('ActivityTitle2', fontSize=12, fontName='Helvetica-Bold',
                                     textColor=WHITE, alignment=TA_CENTER)
        title_bar = Table([[Paragraph('16 PF Trait Assessment - Details', title_style)]],
                         colWidths=[total_width - logo_size - 0.15*inch])
        title_bar.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), GREEN_PRIMARY),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        # Combine avatar and title
        header_table = Table([[avatar_img, title_bar]], 
                           colWidths=[logo_size + 0.05*inch, total_width - logo_size - 0.05*inch])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Descriptors header
        desc_style = ParagraphStyle('DescHeader2', fontSize=11, fontName='Helvetica-Bold',
                                   textColor=WHITE, alignment=TA_CENTER)
        desc_bar = Table([[Paragraph('Descriptors: 16 Personality Factors (PF)', desc_style)]],
                        colWidths=[total_width])
        desc_bar.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), GREEN_PRIMARY),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(desc_bar)
        elements.append(Spacer(1, 0.1*inch))
        
        # Create the scores table
        elements.append(self._create_16pf_activity_table(personality_data, page=2))
        
        return elements
    
    def _create_16pf_activity_table(self, personality_data, page=1):
        """Create the 16PF activity table with Trait, Score, and Rationale for score columns"""
        total_width = self.page_width - 2*self.margin
        
        # Column widths: Trait (narrow), Score (narrow), Rationale (wide)
        trait_col_width = 2.0*inch
        score_col_width = 0.8*inch
        rationale_col_width = total_width - trait_col_width - score_col_width
        
        # Define the 16 factors with their full names and alternate keys for matching
        # Format: (display_name, primary_key, alternate_keys)
        all_factors = [
            ('Factor A:\nCool - warm', 'Warmth', ['Factor A', 'A', 'Warmth']),
            ('Factor B:\nConcrete - Abstract\nthinking', 'Reasoning', ['Factor B', 'B', 'Reasoning']),
            ('Factor C:\nAffected by Feeling -\nEmotionally Stable', 'Emotional Stability', ['Factor C', 'C', 'Emotional Stability']),
            ('Factor E:\nSubmissive - Dominant', 'Dominance', ['Factor E', 'E', 'Dominance']),
            ('Factor F:\nSober - Enthusiastic', 'Liveliness', ['Factor F', 'F', 'Liveliness']),
            ('Factor G:\nExpedient -\nConscientious', 'Rule-Consciousness', ['Factor G', 'G', 'Rule-Consciousness']),
            ('Factor H:\nShy - Bold', 'Social Boldness', ['Factor H', 'H', 'Social Boldness']),
            ('Factor I:\nTough minded -\nTender minded', 'Sensitivity', ['Factor I', 'I', 'Sensitivity']),
            ('Factor L:\nTrusting - Suspicious', 'Vigilance', ['Factor L', 'L', 'Vigilance']),
            ('Factor M:\nPractical - Imaginative', 'Abstractedness', ['Factor M', 'M', 'Abstractedness']),
            ('Factor N:\nForthright - Shrewd', 'Privateness', ['Factor N', 'N', 'Privateness']),
            ('Factor O:\nSelf assured -\nApprehensive', 'Apprehension', ['Factor O', 'O', 'Apprehension']),
            ('Factor Q1:\nConservative -\nExperimenting', 'Openness to Change', ['Factor Q1', 'Q1', 'Openness to Change']),
            ('Factor Q2:\nGroup oriented -\nSelf-sufficient', 'Self-Reliance', ['Factor Q2', 'Q2', 'Self-Reliance']),
            ('Factor Q3:\nUndisciplined -\nFollowing self-image', 'Perfectionism', ['Factor Q3', 'Q3', 'Perfectionism']),
            ('Factor Q4:\nRelaxed - Tense', 'Tension', ['Factor Q4', 'Q4', 'Tension']),
        ]
        
        # Select factors based on page
        if page == 1:
            factors = all_factors[:8]  # A through H (first 8)
        else:
            factors = all_factors[8:]  # I through Q4 (remaining 8)
        
        # Convert personality_data to a dict for easy lookup
        score_dict = {}
        if personality_data:
            for item in personality_data:
                if isinstance(item, dict):
                    # Handle dict format with 'trait', 'name', or 'score'
                    trait_name = item.get('trait', item.get('name', ''))
                    score = item.get('score', 0)
                elif isinstance(item, (tuple, list)) and len(item) >= 2:
                    # Handle tuple/list format (trait_name, score, target)
                    trait_name = item[0]
                    score = item[1]
                else:
                    continue
                
                # Store with original key and normalized versions
                if trait_name:
                    score_dict[str(trait_name)] = score
                    score_dict[str(trait_name).lower()] = score
                    score_dict[str(trait_name).replace(' ', '').lower()] = score
        
        # Styles
        header_style = ParagraphStyle('TableHeader', fontSize=10, fontName='Helvetica-Bold',
                                     textColor=WHITE, alignment=TA_CENTER)
        trait_style = ParagraphStyle('TraitCell', fontSize=9, fontName='Helvetica-Bold',
                                    textColor=colors.HexColor('#006837'), alignment=TA_LEFT,
                                    leading=11)
        score_style = ParagraphStyle('ScoreCell', fontSize=9, alignment=TA_CENTER)
        rationale_style = ParagraphStyle('RationaleCell', fontSize=8, alignment=TA_LEFT,
                                        leading=10, textColor=colors.HexColor('#333333'))
        
        # Build table data
        table_data = [
            [Paragraph('Trait', header_style),
             Paragraph('Score', header_style),
             Paragraph('Rationale for score', header_style)]
        ]
        
        for factor_name, primary_key, alternate_keys in factors:
            # Look up score - try all possible keys
            score = None
            
            # Try primary key first
            for key_variant in [primary_key, primary_key.lower(), primary_key.replace(' ', '').lower()]:
                if key_variant in score_dict:
                    score = score_dict[key_variant]
                    break
            
            # Try alternate keys if not found
            if score is None:
                for alt_key in alternate_keys:
                    for key_variant in [alt_key, alt_key.lower(), alt_key.replace(' ', '').lower()]:
                        if key_variant in score_dict:
                            score = score_dict[key_variant]
                            break
                    if score is not None:
                        break
            
            # Format score
            if isinstance(score, (int, float)):
                score_text = f"{score:.0f}" if score == int(score) else f"{score:.1f}"
            else:
                score_text = str(score) if score else ''
            
            # Rationale is empty for now - can be populated from API response
            rationale_text = ''
            
            table_data.append([
                Paragraph(factor_name, trait_style),
                Paragraph(score_text, score_style),
                Paragraph(rationale_text, rationale_style)
            ])
        
        # Create table
        activity_table = Table(table_data, colWidths=[trait_col_width, score_col_width, rationale_col_width])
        activity_table.setStyle(TableStyle([
            # Header row styling
            ('BACKGROUND', (0, 0), (-1, 0), GREEN_PRIMARY),
            ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#999999')),
            # Alignment
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            # Padding
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            # Alternating row colors
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9F9F9')]),
        ]))
        
        return activity_table
    
    def _create_16pf_reference_table(self):
        """Create the 16PF Low Score / High Score reference table"""
        elements = []
        from flask import current_app
        
        # Add Personality Fit banner at top
        personality_fit_img = os.path.join(current_app.root_path, 'static', 'images', 'personality fit.png')
        if os.path.exists(personality_fit_img):
            banner_width = self.page_width - 2*self.margin
            banner_height = banner_width / 4.82
            banner_img = Image(personality_fit_img, width=banner_width, height=banner_height)
            elements.append(banner_img)
        elements.append(Spacer(1, 0.3*inch))
        
        # 16PF factor data - all 16 factors
        factors = [
            {'left': 'A: Cool, reserved, impersonal, detached formal, aloof',
             'right': 'A: Warm, outgoing, kindly, easygoing, participating and likes people'},
            {'left': 'B: Concrete thinking, less intelligent',
             'right': 'B: Abstract thinking, more intelligent and bright'},
            {'left': 'C: Affected by feelings; emotionally less stable, easily annoyed',
             'right': 'C: Emotionally stable, mature, calm, realistic'},
            {'left': 'E: Submissive, humble, accommodating, mild, easily led',
             'right': 'E: Dominant, assertive, aggressive, competitive, self-assured, authoritative and stubborn'},
            {'left': 'F: Sober, Restrained, prudent, taciturn, serious, introspective and pessimistic',
             'right': 'F: Enthusiastic, spontaneous, expressive, cheerful, talkative, carefree'},
            {'left': 'G:Expedient, disregards rules; self-indulgent, casual, unsteady',
             'right': 'G:Conscientious, conforming, moralistic, responsible; dominated by duty, staid, rule-bound'},
            {'left': 'H:Shy, timid, hesitant, intimidated, threat sensitive',
             'right': 'H:Bold, venturesome, uninhibited; emotionally expressive; handles stress well'},
            {'left': 'I:Tough-minded, self-reliant, realistic, no-nonsense, rough',
             'right': 'I:Tender-minded, sensitive, intuitive, refined'},
            {'left': 'L: Trusting, accepting conditions, easy to get on with',
             'right': 'L:Suspicious, hard to fool, distrustful, skeptical'},
            {'left': 'M:Practical, concerned with down-to-earth, steady',
             'right': 'M: Imaginative, absent minded, absorbed in thought and impractical'},
            {'left': 'N: Forthright, open, genuine, unpretentious, artless',
             'right': 'N: Shrewd, polished, socially aware, diplomatic, and calculating'},
            {'left': 'O: Self-assured, secure, feels free guilt, untroubled, self-satisfied',
             'right': 'O: Apprehensive, self-blaming, insecure, guilt-prone, worrying'},
            {'left': 'Q1: Conservative, respecting traditional ideas',
             'right': 'Q1: Liberal, critical, open to change; experimental'},
            {'left': 'Q2: Group-oriented, follower, listens to others',
             'right': 'Q2: Self-sufficient, resourceful, prefers independent decisions'},
            {'left': 'Q3: Undisciplined self-conflict, lax, careless of social rules',
             'right': 'Q3: Following self image, socially precise, compulsive'},
            {'left': 'Q4: Relaxed, tranquil, composed, low drive, unfrustrated',
             'right': 'Q4: Tense, frustrated, overwrought, has high drive'},
        ]
        
        # Table header
        total_width = self.page_width - 2*self.margin
        col_width = total_width / 2
        
        header_style = ParagraphStyle('RefHeader', fontSize=10, fontName='Helvetica-Bold',
                                      textColor=colors.HexColor('#333333'), alignment=TA_CENTER)
        
        # Create table data
        table_data = [
            [Paragraph('Low Score', header_style), Paragraph('High Score', header_style)]
        ]
        
        # Cell styles
        left_style = ParagraphStyle('LeftCell', fontSize=8, textColor=colors.HexColor('#333333'),
                                    alignment=TA_LEFT, leading=10)
        right_style = ParagraphStyle('RightCell', fontSize=8, textColor=colors.HexColor('#333333'),
                                     alignment=TA_LEFT, leading=10)
        
        for factor in factors:
            # Parse left side - bold the factor code
            left_text = factor['left']
            # Find the colon and make the part before it bold
            if ':' in left_text:
                parts = left_text.split(':', 1)
                left_formatted = f"<b>{parts[0]}:</b>{parts[1]}"
            else:
                left_formatted = left_text
            
            right_text = factor['right']
            if ':' in right_text:
                parts = right_text.split(':', 1)
                right_formatted = f"<b>{parts[0]}:</b>{parts[1]}"
            else:
                right_formatted = right_text
            
            table_data.append([
                Paragraph(left_formatted, left_style),
                Paragraph(right_formatted, right_style)
            ])
        
        # Create table
        ref_table = Table(table_data, colWidths=[col_width, col_width])
        ref_table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F5F5F5')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            # All cells
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            # Borders
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
            # Alternate row colors
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#FAFAFA')]),
        ]))
        
        elements.append(ref_table)
        
        return elements

    def _create_16pf_score_table(self, personality_data):
        """Create the 16PF personality score table with left trait, score bar, right trait"""
        elements = []
        
        # Calculate column widths - more balanced layout
        total_width = self.page_width - 2*self.margin
        left_trait_width = 1.5*inch
        score_col_width = 0.5*inch  # "Score" label column - wider to fit text
        right_trait_width = 1.5*inch
        bar_width = total_width - left_trait_width - score_col_width - right_trait_width
        
        # Green header bar
        header_style = ParagraphStyle('ScoreHeader', fontSize=9, alignment=TA_CENTER, 
                                      fontName='Helvetica-Bold', textColor=WHITE)
        
        # Header cells: [Left Trait | Score | 2 | 4 | 6 | 8 | 10 | Right Trait]
        # The bar area is divided into 5 segments for 2,4,6,8,10
        segment_width = bar_width / 5
        header_cells = [
            Paragraph('', header_style),  # Left trait
            Paragraph('Score', header_style),  # Score label
            Paragraph('2', header_style),
            Paragraph('4', header_style),
            Paragraph('6', header_style),
            Paragraph('8', header_style),
            Paragraph('10', header_style),
            Paragraph('', header_style),  # Right trait
        ]
        
        col_widths = [left_trait_width, score_col_width, segment_width, segment_width, segment_width, segment_width, segment_width, right_trait_width]
        
        header_table = Table([header_cells], colWidths=col_widths, rowHeights=[0.28*inch])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), GREEN_PRIMARY),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(header_table)
        
        # Create data rows
        for trait in personality_data:
            # Get trait data
            left_name = trait.get('left_name', trait.get('name', ''))
            left_desc = trait.get('left_desc', trait.get('desc', ''))
            right_name = trait.get('right_name', '')
            right_desc = trait.get('right_desc', '')
            score = trait.get('score', 5)
            target = trait.get('target', 5)
            
            # Left trait cell
            left_name_style = ParagraphStyle('LeftName', fontSize=8, fontName='Helvetica-Bold', 
                                             textColor=GREEN_PRIMARY, alignment=TA_LEFT, leading=10)
            left_desc_style = ParagraphStyle('LeftDesc', fontSize=7, textColor=colors.HexColor('#666666'),
                                             fontName='Helvetica-Oblique', alignment=TA_LEFT, leading=9)
            left_cell = Table([
                [Paragraph(left_name, left_name_style)],
                [Paragraph(left_desc, left_desc_style)]
            ], colWidths=[left_trait_width - 5])
            left_cell.setStyle(TableStyle([
                ('LEFTPADDING', (0, 0), (-1, -1), 3),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ]))
            
            # Score value cell
            score_style = ParagraphStyle('ScoreVal', fontSize=10, fontName='Helvetica-Bold',
                                         textColor=GREEN_PRIMARY, alignment=TA_CENTER)
            score_cell = Paragraph(str(int(score)), score_style)
            
            # Create score bar drawing that spans 5 columns
            score_bar = self._create_16pf_full_score_bar(score, target, bar_width)
            
            # Right trait cell
            right_name_style = ParagraphStyle('RightName', fontSize=8, fontName='Helvetica-Bold',
                                              textColor=GREEN_PRIMARY, alignment=TA_LEFT, leading=10)
            right_desc_style = ParagraphStyle('RightDesc', fontSize=7, textColor=colors.HexColor('#666666'),
                                              fontName='Helvetica-Oblique', alignment=TA_LEFT, leading=9)
            right_cell = Table([
                [Paragraph(right_name, right_name_style)],
                [Paragraph(right_desc, right_desc_style)]
            ], colWidths=[right_trait_width - 5])
            right_cell.setStyle(TableStyle([
                ('LEFTPADDING', (0, 0), (-1, -1), 3),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ]))
            
            # Build row: [left_trait | score_val | score_bar (spans 5 cols) | right_trait]
            # We need to merge cells for the score bar
            row_cells = [left_cell, score_cell, score_bar, '', '', '', '', right_cell]
            
            row_table = Table([row_cells], colWidths=col_widths, rowHeights=[0.55*inch])
            row_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (1, 0), (1, 0), 'CENTER'),  # Score value centered
                ('SPAN', (2, 0), (6, 0)),  # Merge score bar cells
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#E0E0E0')),
                ('LINEAFTER', (0, 0), (0, 0), 0.5, colors.HexColor('#E0E0E0')),
                ('LINEAFTER', (1, 0), (1, 0), 0.5, colors.HexColor('#E0E0E0')),
                ('LINEAFTER', (6, 0), (6, 0), 0.5, colors.HexColor('#E0E0E0')),
            ]))
            elements.append(row_table)
        
        elements.append(Spacer(1, 0.2*inch))
        
        # Legend at bottom (centered) - only User Score with circle
        legend_style = ParagraphStyle('LegendStyle', fontSize=10, alignment=TA_CENTER)
        legend = Paragraph('● User Score', legend_style)
        elements.append(legend)
        
        return elements
    
    def _create_16pf_full_score_bar(self, score, target, bar_width):
        """Create the full score bar with gradient and markers"""
        bar_height = 12
        drawing_height = 25
        
        d = Drawing(bar_width, drawing_height)
        
        # Calculate the bar Y position (centered in drawing)
        bar_y = (drawing_height - bar_height) / 2
        
        # Create gradient bar segments (red → yellow → green)
        # Divide into 10 segments for smooth gradient
        segment_w = bar_width / 10
        
        for i in range(10):
            x = i * segment_w
            # Color gradient: red (0-3), yellow (4-6), green (7-10)
            if i < 3:
                # Red to orange
                r = 0.86
                g = 0.2 + (i * 0.15)
                b = 0.27
            elif i < 6:
                # Orange to yellow-green
                r = 0.86 - ((i - 3) * 0.15)
                g = 0.65 + ((i - 3) * 0.1)
                b = 0.2
            else:
                # Yellow-green to green
                r = 0.16 - ((i - 6) * 0.02)
                g = 0.65 + ((i - 6) * 0.05)
                b = 0.31
            
            seg_color = colors.Color(r, g, b)
            d.add(Rect(x, bar_y, segment_w + 1, bar_height, fillColor=seg_color, strokeColor=None))
        
        # Add vertical dividers at segment boundaries (every 1/5 of the bar)
        # These align with the header columns for 2, 4, 6, 8
        for i in [1, 2, 3, 4]:  # Dividers at 20%, 40%, 60%, 80%
            x = i * (bar_width / 5)
            d.add(Line(x, bar_y - 2, x, bar_y + bar_height + 2, strokeColor=WHITE, strokeWidth=1.5))
        
        # User score marker (filled circle with border)
        score_x = (score / 10) * bar_width
        d.add(Circle(score_x, bar_y + bar_height/2, 5, fillColor=WHITE, strokeColor=colors.HexColor('#333333'), strokeWidth=2))
        
        return d

    def _create_score_cell(self, score, target, cell_start, cell_end, cell_width):
        """Create a score cell with markers if score/target falls within range"""
        d = Drawing(cell_width, 30)
        
        # Calculate positions within cell (0 to cell_width)
        # Score/target are on 0-10 scale, cell covers cell_start to cell_end
        
        # Check if score is in this cell - draw filled circle
        if cell_start < score <= cell_end:
            pos = ((score - cell_start) / 2) * cell_width
            # Draw circle marker
            d.add(Circle(pos, 15, 5, fillColor=colors.HexColor('#333333'), strokeColor=None))
        
        return d

    def _create_16pf_score_bar(self, score, target):
        """Create a horizontal score bar for 16PF traits (1-10 scale)"""
        bar_width = 3.5 * inch
        bar_height = 15
        
        d = Drawing(bar_width, bar_height + 10)
        
        # Background bar (gray)
        d.add(Rect(0, 5, bar_width, bar_height, fillColor=colors.HexColor('#E5E5E5'), strokeColor=None))
        
        # Score bar (gradient from red to green based on position)
        score_width = (score / 10) * bar_width
        # Color based on score position
        if score <= 3:
            bar_color = colors.HexColor('#DC3545')  # Red
        elif score <= 5:
            bar_color = colors.HexColor('#FFC107')  # Yellow
        else:
            bar_color = colors.HexColor('#28A745')  # Green
        
        d.add(Rect(0, 5, score_width, bar_height, fillColor=bar_color, strokeColor=None))
        
        # Column dividers at 2, 4, 6, 8
        for i in [2, 4, 6, 8]:
            x = (i / 10) * bar_width
            d.add(Line(x, 3, x, bar_height + 7, strokeColor=WHITE, strokeWidth=1))
        
        # Score marker (filled circle)
        score_x = (score / 10) * bar_width
        d.add(Circle(score_x, bar_height/2 + 5, 5, fillColor=WHITE, strokeColor=GREEN_PRIMARY, strokeWidth=2))
        
        return d
    
    def generate_cluster_score_page(self, cluster_name, cluster_score, competencies,
                                    overused_competencies=None, client_logo_path=None,
                                    feedback_name=None, feedback_score=None, feedback_max=None,
                                    activity_stats=None):
        """Generate the Competency Score by Cluster page"""
        elements = []
        from flask import current_app
        
        # Header with logos
        traj_logo = os.path.join(current_app.root_path, 'static', 'images', 'logo-trajectorie-codrive.png')
        elements.append(self._create_logo_header(traj_logo, client_logo_path))
        elements.append(Spacer(1, 0.2*inch))
        
        # Competency Score by Cluster banner - use image
        cluster_banner_img = os.path.join(current_app.root_path, 'static', 'images', 'compscorebycluster.png')
        if os.path.exists(cluster_banner_img):
            banner_width = self.page_width - 2*self.margin
            banner_height = banner_width / 4.82  # Maintain aspect ratio
            banner_img = Image(cluster_banner_img, width=banner_width, height=banner_height)
            elements.append(banner_img)
        else:
            elements.append(self._create_header_banner('Competency Score by Cluster', GREEN_PRIMARY))
        elements.append(Spacer(1, 0.2*inch))
        
        # Cluster name header (green bar) with overall score
        cluster_header = Table([[Paragraph(f'<font color="white"><b>Overall &lt;{cluster_name}&gt;: {cluster_score}%</b></font>',
                                           ParagraphStyle('ClusterHeader', fontSize=12, alignment=TA_CENTER))]],
                              colWidths=[self.page_width - 2*self.margin])
        cluster_header.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), GREEN_PRIMARY),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(cluster_header)
        elements.append(Spacer(1, 0.15*inch))
        
        # Critical Conversations section with logo and info
        meeting_logo = os.path.join(current_app.root_path, 'static', 'images', 'meeting.png')
        logo_size = 0.9*inch
        if os.path.exists(meeting_logo):
            conv_logo = Image(meeting_logo, width=logo_size, height=logo_size)
        else:
            conv_logo = Table([['👥']], colWidths=[logo_size], rowHeights=[logo_size])
            conv_logo.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#E0E0E0')),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTSIZE', (0, 0), (-1, -1), 24),
            ]))
        
        # Critical Conversations title bar - full page width, center aligned
        total_width = self.page_width - 2*self.margin
        conv_title_style = ParagraphStyle('ConvTitle', fontSize=12, fontName='Helvetica-Bold',
                                          textColor=WHITE, alignment=TA_CENTER)
        conv_title_bar = Table([[Paragraph('CRITICAL CONVERSATIONS', conv_title_style)]],
                              colWidths=[total_width])
        conv_title_bar.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), GREEN_PRIMARY),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        elements.append(conv_title_bar)
        elements.append(Spacer(1, 0.08*inch))
        
        # Info text for conversations - use activity_stats if provided
        info_label_style = ParagraphStyle('ConvInfoLabel', fontSize=9, fontName='Helvetica-Bold', leading=14)
        info_val_style = ParagraphStyle('ConvInfoVal', fontSize=9, leading=14)
        
        # Get values from activity_stats or use defaults
        total_conv = activity_stats.get('total', 2) if activity_stats else 2
        attempted_conv = activity_stats.get('attempted', 2) if activity_stats else 2
        time_available = activity_stats.get('time_available', '1Hr : 39Min') if activity_stats else '1Hr : 39Min'
        time_taken = activity_stats.get('time_taken', '0Hr : 41Min') if activity_stats else '0Hr : 41Min'
        
        conv_info_table = Table([
            [Paragraph('Total Conversations', info_label_style), 
             Paragraph(f'- {total_conv}', info_val_style),
             Paragraph('Time available', info_label_style), 
             Paragraph(f'- {time_available}', info_val_style)],
            [Paragraph('Attempted Conversations', info_label_style), 
             Paragraph(f'- {attempted_conv}', info_val_style),
             Paragraph('Time taken', info_label_style), 
             Paragraph(f'- {time_taken}', info_val_style)],
        ], colWidths=[1.5*inch, 0.4*inch, 1.1*inch, 1.1*inch])
        conv_info_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ]))
        
        # Logo and info side by side
        conv_header = Table([[conv_logo, conv_info_table]], colWidths=[logo_size + 0.1*inch, total_width - logo_size - 0.1*inch])
        conv_header.setStyle(TableStyle([
            ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
            ('VALIGN', (1, 0), (1, 0), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (0, 0), 0),
            ('LEFTPADDING', (1, 0), (1, 0), 10),
        ]))
        elements.append(conv_header)
        
        # Green bar below
        green_bar = Table([['']], colWidths=[total_width], rowHeights=[0.15*inch])
        green_bar.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), GREEN_PRIMARY),
        ]))
        elements.append(green_bar)
        
        # Competency table - sort alphabetically by competency name
        if competencies:
            sorted_competencies = sorted(competencies, key=lambda x: x.get('name', '').lower())
            elements.append(self._create_competency_table_v2(sorted_competencies))
        
        elements.append(Spacer(1, 0.2*inch))
        
        # Legend
        legend_style = ParagraphStyle('LegendStyle', fontSize=9, alignment=TA_LEFT)
        legend_table = Table([
            [Paragraph('● User Score', legend_style)]
        ], colWidths=[1.2*inch])
        legend_table.setStyle(TableStyle([
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ]))
        elements.append(legend_table)
        
        # Overused competencies section - only show if raw_score > max_score
        overused = []
        if competencies:
            for comp in competencies:
                raw_score = comp.get('raw_score', 0)
                max_score = comp.get('max_score', 3)
                if raw_score > max_score:
                    overused.append(comp)
        
        if overused:
            elements.append(Spacer(1, 0.2*inch))
            elements.extend(self._create_balance_scale_section(overused))
        
        elements.append(PageBreak())
        return elements
    
    def _create_competency_table_v2(self, competencies):
        """Create the competency table matching the reference design"""
        total_width = self.page_width - 2*self.margin
        
        # Column widths: Competency Name | Score% | 5 score columns
        comp_col_width = 1.4*inch
        score_col_width = 0.4*inch
        bar_col_width = (total_width - comp_col_width - score_col_width) / 5
        
        # Header row
        header_style = ParagraphStyle('CompHeader', fontSize=7, fontName='Helvetica-Bold',
                                      textColor=colors.HexColor('#333333'), alignment=TA_CENTER, leading=9)
        
        header_row = [
            Paragraph('', header_style),  # Competency name col
            Paragraph('', header_style),  # Score % col
            Paragraph('Significant<br/>Shortcoming', header_style),
            Paragraph('Needs<br/>Improvement', header_style),
            Paragraph('Average', header_style),
            Paragraph('Good', header_style),
            Paragraph('Proficient', header_style),
        ]
        
        col_widths = [comp_col_width, score_col_width, bar_col_width, bar_col_width, bar_col_width, bar_col_width, bar_col_width]
        
        table_data = [header_row]
        
        # Competency rows
        name_style = ParagraphStyle('CompName', fontSize=8, fontName='Helvetica-Bold',
                                    textColor=colors.HexColor('#8B0000'), alignment=TA_LEFT, leading=10)
        desc_style = ParagraphStyle('CompDesc', fontSize=6, fontName='Helvetica-Oblique',
                                    textColor=colors.HexColor('#666666'), alignment=TA_LEFT, leading=8)
        score_style = ParagraphStyle('CompScore', fontSize=9, fontName='Helvetica-Bold',
                                     textColor=colors.HexColor('#333333'), alignment=TA_CENTER)
        
        for comp in competencies:
            name = comp.get('name', '')
            level = comp.get('level', 'Basic')
            description = comp.get('description', '')
            score = comp.get('score', 0)
            target = comp.get('target', 60)
            
            # Competency name cell with level and description
            name_cell = Table([
                [Paragraph(f'{name} ({level})', name_style)],
                [Paragraph(description, desc_style)]
            ], colWidths=[comp_col_width - 5])
            name_cell.setStyle(TableStyle([
                ('LEFTPADDING', (0, 0), (-1, -1), 2),
                ('TOPPADDING', (0, 0), (-1, -1), 1),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ]))
            
            # Score percentage
            score_pct = f"{int(score)}%"
            
            # Create score bar spanning 5 columns
            score_bar = self._create_competency_bar_v2(score, target, bar_col_width * 5)
            
            row = [name_cell, Paragraph(score_pct, score_style), score_bar, '', '', '', '']
            table_data.append(row)
        
        # Create table
        comp_table = Table(table_data, colWidths=col_widths)
        comp_table.setStyle(TableStyle([
            # Header row styling
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F5F5F5')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            # Span score bar across 5 columns
            ('SPAN', (2, 1), (6, 1)),
            ('SPAN', (2, 2), (6, 2)),
            ('SPAN', (2, 3), (6, 3)),
            ('SPAN', (2, 4), (6, 4)),
            ('SPAN', (2, 5), (6, 5)),
            ('SPAN', (2, 6), (6, 6)),
            ('SPAN', (2, 7), (6, 7)),
            ('SPAN', (2, 8), (6, 8)),
            ('SPAN', (2, 9), (6, 9)),
            ('SPAN', (2, 10), (6, 10)),
            # Borders
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
            # Padding
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ]))
        
        return comp_table
    
    def _create_competency_bar_v2(self, score, target, bar_width):
        """Create a competency score bar with gradient and markers"""
        bar_height = 10
        drawing_height = 30
        
        d = Drawing(bar_width, drawing_height)
        
        # Bar Y position
        bar_y = (drawing_height - bar_height) / 2
        
        # Score is 0-100, divide bar into 5 segments (0-20, 20-40, 40-60, 60-80, 80-100)
        segment_width = bar_width / 5
        
        # Draw bar segments with gradient colors (red to green)
        # User score fills from left
        score_width = (score / 100) * bar_width
        
        # Background (gray)
        d.add(Rect(0, bar_y, bar_width, bar_height, fillColor=colors.HexColor('#E5E5E5'), strokeColor=None))
        
        # Score bar (red to green gradient based on score position)
        for i in range(5):
            seg_start = i * segment_width
            seg_end = (i + 1) * segment_width
            
            # Color gradient: red (0-20), orange-red (20-40), yellow (40-60), yellow-green (60-80), green (80-100)
            if i == 0:
                seg_color = colors.HexColor('#8B4513')  # Brown/dark red
            elif i == 1:
                seg_color = colors.HexColor('#CD5C5C')  # Indian red
            elif i == 2:
                seg_color = colors.HexColor('#DAA520')  # Goldenrod
            elif i == 3:
                seg_color = colors.HexColor('#9ACD32')  # Yellow-green
            else:
                seg_color = colors.HexColor('#228B22')  # Forest green
            
            # Only fill up to score
            if score_width > seg_start:
                fill_width = min(segment_width, score_width - seg_start)
                if fill_width > 0:
                    d.add(Rect(seg_start, bar_y, fill_width, bar_height, fillColor=seg_color, strokeColor=None))
        
        # Column dividers
        for i in range(1, 5):
            x = i * segment_width
            d.add(Line(x, bar_y - 2, x, bar_y + bar_height + 2, strokeColor=WHITE, strokeWidth=1))
        
        # User score marker (circle) - white with dark border
        score_x = (score / 100) * bar_width
        d.add(Circle(score_x, bar_y + bar_height/2, 5, fillColor=WHITE, strokeColor=colors.HexColor('#333333'), strokeWidth=2))
        
        return d
    
    def generate_activity_score_page(self, activity_name, activity_stats, topic_name,
                                     topic_score, competencies, overused_competencies=None,
                                     client_logo_path=None, feedback_name=None, feedback_score=None,
                                     feedback_max=None):
        """Generate the Competency Score by Activity page"""
        elements = []
        from flask import current_app
        
        # Header with logos
        traj_logo = os.path.join(current_app.root_path, 'static', 'images', 'logo-trajectorie-codrive.png')
        elements.append(self._create_logo_header(traj_logo, client_logo_path))
        elements.append(Spacer(1, 0.2*inch))
        
        # Competency Score by Activity banner - use image
        activity_banner_img = os.path.join(current_app.root_path, 'static', 'images', 'compscorebyact.png')
        if os.path.exists(activity_banner_img):
            banner_width = self.page_width - 2*self.margin
            banner_height = banner_width / 4.82  # Maintain aspect ratio
            banner_img = Image(activity_banner_img, width=banner_width, height=banner_height)
            elements.append(banner_img)
        else:
            elements.append(self._create_header_banner('Competency Score by Activity', GREEN_PRIMARY))
        elements.append(Spacer(1, 0.15*inch))
        
        # Critical Conversations section with logo and info (same as cluster page)
        meeting_logo = os.path.join(current_app.root_path, 'static', 'images', 'meeting.png')
        total_width = self.page_width - 2*self.margin
        logo_size = 0.9*inch
        if os.path.exists(meeting_logo):
            conv_logo = Image(meeting_logo, width=logo_size, height=logo_size)
        else:
            conv_logo = Table([['👥']], colWidths=[logo_size], rowHeights=[logo_size])
            conv_logo.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#E0E0E0')),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTSIZE', (0, 0), (-1, -1), 24),
            ]))
        
        # Critical Conversations title bar - full page width, center aligned
        conv_title_style = ParagraphStyle('ConvTitle2', fontSize=12, fontName='Helvetica-Bold',
                                          textColor=WHITE, alignment=TA_CENTER)
        conv_title_bar = Table([[Paragraph('CRITICAL CONVERSATIONS', conv_title_style)]],
                              colWidths=[total_width])
        conv_title_bar.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), GREEN_PRIMARY),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        elements.append(conv_title_bar)
        elements.append(Spacer(1, 0.08*inch))
        
        # Info text for conversations
        info_label_style = ParagraphStyle('ConvInfoLabel2', fontSize=9, fontName='Helvetica-Bold', leading=14)
        info_val_style = ParagraphStyle('ConvInfoVal2', fontSize=9, leading=14)
        
        total_conv = activity_stats.get('total', 2) if activity_stats else 2
        attempted_conv = activity_stats.get('attempted', 2) if activity_stats else 2
        time_available = activity_stats.get('time_available', '1Hr : 39Min') if activity_stats else '1Hr : 39Min'
        time_taken = activity_stats.get('time_taken', '0Hr : 41Min') if activity_stats else '0Hr : 41Min'
        
        conv_info_table = Table([
            [Paragraph('Total Conversations', info_label_style), 
             Paragraph(f'- {total_conv}', info_val_style),
             Paragraph('Time available', info_label_style), 
             Paragraph(f'- {time_available}', info_val_style)],
            [Paragraph('Attempted Conversations', info_label_style), 
             Paragraph(f'- {attempted_conv}', info_val_style),
             Paragraph('Time taken', info_label_style), 
             Paragraph(f'- {time_taken}', info_val_style)],
        ], colWidths=[1.5*inch, 0.4*inch, 1.1*inch, 1.1*inch])
        conv_info_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ]))
        
        # Logo and info side by side
        conv_header = Table([[conv_logo, conv_info_table]], colWidths=[logo_size + 0.1*inch, total_width - logo_size - 0.1*inch])
        conv_header.setStyle(TableStyle([
            ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
            ('VALIGN', (1, 0), (1, 0), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (0, 0), 0),
            ('LEFTPADDING', (1, 0), (1, 0), 10),
        ]))
        elements.append(conv_header)
        elements.append(Spacer(1, 0.15*inch))
        
        # Topic header with percentage - bright green bar
        topic_header = Table([[Paragraph(f'<font color="white"><b>Topic - {topic_name}: {topic_score}%</b></font>',
                                         ParagraphStyle('TopicHeader', fontSize=14, alignment=TA_CENTER))]],
                            colWidths=[total_width])
        topic_header.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#4CAF50')),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))
        elements.append(topic_header)
        elements.append(Spacer(1, 0.1*inch))
        
        # Competency table using the new v2 style
        if competencies:
            sorted_competencies = sorted(competencies, key=lambda x: x.get('name', '').lower())
            elements.append(self._create_competency_table_v2(sorted_competencies))
        
        elements.append(Spacer(1, 0.2*inch))
        
        # Overused competencies section - only show if raw_score > max_score
        overused = []
        if competencies:
            for comp in competencies:
                raw_score = comp.get('raw_score', 0)
                max_score = comp.get('max_score', 3)
                if raw_score > max_score:
                    overused.append(comp)
        
        if overused:
            elements.append(Spacer(1, 0.2*inch))
            elements.extend(self._create_balance_scale_section(overused))
        
        elements.append(PageBreak())
        return elements
    
    def _create_balance_scale_section(self, overused_competencies):
        """Create the balance scale section showing overused competencies.
        Only shows if there is at least one overused competency.
        Displays the stone balance image centered, with red tiles below side by side.
        """
        elements = []
        from flask import current_app
        
        # Only show if there are overused competencies
        if not overused_competencies or len(overused_competencies) == 0:
            return elements
        
        total_width = self.page_width - 2*self.margin
        
        # Balance scale image - centered, no text
        balance_img_path = os.path.join(current_app.root_path, 'static', 'images', 'balancescale.png')
        if not os.path.exists(balance_img_path):
            balance_img_path = os.path.join(current_app.root_path, 'static', 'images', 'balance_scale.png')
        
        if os.path.exists(balance_img_path):
            # Center the image
            img_width = 3*inch
            img_height = 2.1*inch
            balance_img = Image(balance_img_path, width=img_width, height=img_height)
            
            # Wrap in table to center
            img_table = Table([[balance_img]], colWidths=[total_width])
            img_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(img_table)
        
        elements.append(Spacer(1, 0.15*inch))
        
        # Create red boxes for each overused competency - side by side
        red_boxes = []
        for comp in overused_competencies:
            name = comp.get('name', 'Unknown')
            # Use raw_score if available, otherwise use score
            raw_score = comp.get('raw_score', comp.get('score', 0))
            max_score = comp.get('max_score', 3)
            red_boxes.append(self._create_overused_box(name, raw_score, max_score))
        
        # Arrange boxes side by side (centered)
        num_boxes = len(red_boxes)
        box_width = 1.6*inch
        
        if num_boxes > 0:
            # Create a single row with all boxes
            col_widths = [box_width] * num_boxes
            box_table = Table([red_boxes], colWidths=col_widths, rowHeights=[0.8*inch])
            box_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ]))
            
            # Wrap to center the entire row
            wrapper = Table([[box_table]], colWidths=[total_width])
            wrapper.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ]))
            elements.append(wrapper)
        
        return elements
    
    def _create_feedback_box(self, feedback_name, score, max_score):
        """Create a feedback score box"""
        # Red box with feedback name and score
        box_width = 1.2*inch
        box_height = 0.8*inch
        
        name_style = ParagraphStyle('FeedbackName', fontSize=8, fontName='Helvetica',
                                    textColor=WHITE, alignment=TA_CENTER)
        score_style = ParagraphStyle('FeedbackScore', fontSize=16, fontName='Helvetica-Bold',
                                     textColor=WHITE, alignment=TA_CENTER)
        
        feedback_table = Table([
            [Paragraph(feedback_name, name_style)],
            [Paragraph(f'{score}/{max_score}', score_style)]
        ], colWidths=[box_width], rowHeights=[0.25*inch, 0.4*inch])
        feedback_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#C62828')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        
        return feedback_table

    def generate_competency_descriptors_page(self, competencies, client_logo_path=None, 
                                            include_16pf=True, personality_data=None):
        """Generate Competency Descriptors pages - 16PF factors (if enabled) and competency descriptions"""
        elements = []
        from flask import current_app
        
        total_width = self.page_width - 2*self.margin
        
        # Header with logos
        traj_logo = os.path.join(current_app.root_path, 'static', 'images', 'logo-trajectorie-codrive.png')
        
        # Competency Descriptors banner - use image
        desc_banner_img = os.path.join(current_app.root_path, 'static', 'images', 'compdescriptors.png')
        
        # Only include 16PF descriptors if enabled
        if include_16pf:
            # NEW: Add the two activity score pages first
            # Page 1: Factors A through I with scores and rationales
            elements.extend(self._create_16pf_activity_score_page1(personality_data))
            elements.append(PageBreak())
            
            # Page 2: Factors L through Q4 with scores and rationales
            elements.extend(self._create_16pf_activity_score_page2(personality_data))
            elements.append(PageBreak())
            
            # Then the original 16PF descriptors pages
            elements.append(self._create_logo_header(traj_logo, client_logo_path))
            elements.append(Spacer(1, 0.2*inch))
            
            if os.path.exists(desc_banner_img):
                banner_width = total_width
                banner_height = banner_width / 4.82
                banner_img = Image(desc_banner_img, width=banner_width, height=banner_height)
                elements.append(banner_img)
            else:
                elements.append(self._create_header_banner('Competency Descriptors', GREEN_PRIMARY))
            elements.append(Spacer(1, 0.2*inch))
            
            # 16 Personality Factors section header
            pf_header = Table([[Paragraph('<font color="white"><b>Descriptors: 16 Personality factors (PF)</b></font>',
                                          ParagraphStyle('PFHeader', fontSize=12, alignment=TA_CENTER))]],
                             colWidths=[total_width])
            pf_header.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), GREEN_PRIMARY),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            elements.append(pf_header)
            elements.append(Spacer(1, 0.1*inch))
            
            # Create 16PF descriptors table (first page - Factors A through I)
            elements.append(self._create_16pf_descriptors_table_page1())
            
            elements.append(PageBreak())
            
            # Second page for 16PF (Factors L through Q4)
            elements.append(self._create_logo_header(traj_logo, client_logo_path))
            elements.append(Spacer(1, 0.2*inch))
            
            if os.path.exists(desc_banner_img):
                banner_width = total_width
                banner_height = banner_width / 4.82
                banner_img2 = Image(desc_banner_img, width=banner_width, height=banner_height)
                elements.append(banner_img2)
            else:
                elements.append(self._create_header_banner('Competency Descriptors', GREEN_PRIMARY))
            elements.append(Spacer(1, 0.2*inch))
            
            elements.append(pf_header)
            elements.append(Spacer(1, 0.1*inch))
            
            elements.append(self._create_16pf_descriptors_table_page2())
            
            elements.append(PageBreak())
        
        # Competency Descriptors page (alphabetically sorted) - always included
        elements.append(self._create_logo_header(traj_logo, client_logo_path))
        elements.append(Spacer(1, 0.2*inch))
        
        if os.path.exists(desc_banner_img):
            banner_width = total_width
            banner_height = banner_width / 4.82
            banner_img3 = Image(desc_banner_img, width=banner_width, height=banner_height)
            elements.append(banner_img3)
        else:
            elements.append(self._create_header_banner('Competency Descriptors', GREEN_PRIMARY))
        elements.append(Spacer(1, 0.2*inch))
        
        # Competency Descriptors header
        comp_header = Table([[Paragraph('<font color="white"><b>Competency Descriptors</b></font>',
                                        ParagraphStyle('CompDescHeader', fontSize=12, alignment=TA_CENTER))]],
                           colWidths=[total_width])
        comp_header.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#666666')),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(comp_header)
        elements.append(Spacer(1, 0.05*inch))
        
        # Sort competencies alphabetically and create table
        if competencies:
            sorted_comps = sorted(competencies, key=lambda x: x.get('name', '').lower())
            elements.append(self._create_competency_descriptors_table(sorted_comps))
        
        elements.append(PageBreak())
        return elements
    
    def _create_16pf_descriptors_table_page1(self):
        """Create 16PF descriptors table for page 1 (Factors A through I)"""
        total_width = self.page_width - 2*self.margin
        col_widths = [0.7*inch, (total_width - 0.7*inch) / 2, (total_width - 0.7*inch) / 2]
        
        # Header row style
        header_style = ParagraphStyle('DescHeader', fontSize=9, fontName='Helvetica-Bold',
                                      textColor=WHITE, alignment=TA_CENTER)
        # Trait name style (green, bold)
        trait_style = ParagraphStyle('TraitName', fontSize=9, fontName='Helvetica-Bold',
                                     textColor=GREEN_PRIMARY, alignment=TA_CENTER)
        # Low/High title style (bold, underlined)
        title_style = ParagraphStyle('TitleStyle', fontSize=9, fontName='Helvetica-Bold',
                                     alignment=TA_CENTER)
        # Description style (italic)
        desc_style = ParagraphStyle('DescStyle', fontSize=8, fontName='Helvetica-Oblique',
                                    alignment=TA_CENTER, leading=10)
        
        # 16PF Factor data for page 1 (A through I)
        factors_page1 = [
            ('Factor A', 'Cool', 'Cool, reserved, impersonal, detached, aloof; prefers things over people; avoids compromise; rigid; critical.',
             'Warm', 'Warm, outgoing, kindly, emotionally expressive; enjoys group settings; cooperative; remembers people\'s names; adaptable.'),
            ('Factor B', 'Concrete Thinking', 'Concrete, less intelligent; takes time to learn; literal in interpretation.',
             'Abstract Thinking', 'Abstract thinker, bright, quick to grasp ideas and concepts; imaginative.'),
            ('Factor C', 'Affected by Feelings', 'Affected by feelings; emotionally unstable; easily annoyed and frustrated; prone to neurotic symptoms.',
             'Emotionally Stable', 'Emotionally stable, mature, calm; realistic and unruffled under pressure.'),
            ('Factor E', 'Submissive', 'Submissive, humble, accommodating; dependent and conforming.',
             'Dominant', 'Dominant, assertive, aggressive, competitive, self-assured, authoritative.'),
            ('Factor F', 'Sober', 'Restrained, prudent, taciturn, serious; introspective and pessimistic.',
             'Enthusiastic', 'Enthusiastic, spontaneous, expressive, cheerful, talkative, carefree.'),
            ('Factor G', 'Expedient', 'Expedient, disregards rules; self-indulgent, casual, unsteady; may be effective when free from group norms, but also antisocial.',
             'Conscientious', 'Conscientious, conforming, moralistic, responsible; dominated by duty; prefers hard work over wit.'),
            ('Factor H', 'Shy', 'Shy, timid, hesitant, intimidated; avoids personal contact and large groups.',
             'Bold', 'Bold, venturesome, uninhibited; emotionally expressive; handles stress well, sociable and outspoken.'),
            ('Factor I', 'Tough Minded', 'Tough-minded, self-reliant, realistic, rough, down-to-earth; skeptical of emotional content; pragmatic.',
             'Tender Minded', 'Tender-minded, sensitive, intuitive, artistic, day-dreaming, dependent, expressive.'),
        ]
        
        # Build table rows
        rows = []
        # Header row
        rows.append([
            Paragraph('Trait', header_style),
            Paragraph('Low score', header_style),
            Paragraph('High', header_style)
        ])
        
        for factor, low_title, low_desc, high_title, high_desc in factors_page1:
            low_cell = [Paragraph(f'<u>{low_title}</u>', title_style),
                       Paragraph(low_desc, desc_style)]
            high_cell = [Paragraph(f'<u>{high_title}</u>', title_style),
                        Paragraph(high_desc, desc_style)]
            
            low_table = Table([[p] for p in low_cell], colWidths=[col_widths[1] - 6])
            low_table.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER')]))
            
            high_table = Table([[p] for p in high_cell], colWidths=[col_widths[2] - 6])
            high_table.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER')]))
            
            rows.append([
                Paragraph(factor, trait_style),
                low_table,
                high_table
            ])
        
        table = Table(rows, colWidths=col_widths)
        table.setStyle(TableStyle([
            # Header styling
            ('BACKGROUND', (0, 0), (-1, 0), GREEN_PRIMARY),
            ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
            # Alignment
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            # Padding
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ]))
        
        return table
    
    def _create_16pf_descriptors_table_page2(self):
        """Create 16PF descriptors table for page 2 (Factors L through Q4)"""
        total_width = self.page_width - 2*self.margin
        col_widths = [0.7*inch, (total_width - 0.7*inch) / 2, (total_width - 0.7*inch) / 2]
        
        header_style = ParagraphStyle('DescHeader2', fontSize=9, fontName='Helvetica-Bold',
                                      textColor=WHITE, alignment=TA_CENTER)
        trait_style = ParagraphStyle('TraitName2', fontSize=9, fontName='Helvetica-Bold',
                                     textColor=GREEN_PRIMARY, alignment=TA_CENTER)
        title_style = ParagraphStyle('TitleStyle2', fontSize=9, fontName='Helvetica-Bold',
                                     alignment=TA_CENTER)
        desc_style = ParagraphStyle('DescStyle2', fontSize=8, fontName='Helvetica-Oblique',
                                    alignment=TA_CENTER, leading=10)
        
        # 16PF Factor data for page 2 (L through Q4)
        factors_page2 = [
            ('Factor L', 'Trusting', 'Trusting, accepting, adaptable, team-oriented, tolerant.',
             'Suspicious', 'Suspicious, skeptical, self-opinionated, egocentric, slow to trust others.'),
            ('Factor M', 'Practical', 'Practical, down-to-earth, detail-focused, steady; good in emergencies; conventional.',
             'Imaginative', 'Imaginative, abstracted, inner-directed, creative, unconventional; sometimes impractical.'),
            ('Factor N', 'Forthright', 'Forthright, open, genuine, unpretentious, artless.',
             'Shrewd', 'Shrewd, polished, socially aware, diplomatic, perceptive, sometimes cynical.'),
            ('Factor O', 'Self-assured', 'Self-assured, secure, untroubled, confident; may be insensitive to feedback.',
             'Apprehensive', 'Apprehensive, self-blaming, insecure, guilt-prone, anxious, socially hesitant.'),
            ('Factor Q1', 'Conservative', 'Traditional, conservative, moralistic, cautious; accepts the "tried and tested," avoids change.',
             'Experimenting', 'Liberal, critical, open to change; experimental, skeptical, interested in new ideas and intellectual matters.'),
            ('Factor Q2', 'Group oriented', 'Group-oriented, follower; seeks approval, prefers group decisions, dependent on others.',
             'Self-sufficient', 'Self-sufficient, resourceful, prefers independent decisions; doesn\'t seek social validation; temperamentally independent.'),
            ('Factor Q3', 'Undisciplined', 'Undisciplined, lax, careless of social rules, impulsive, not detail-oriented.',
             'Following self-image', 'Compulsive, socially precise, perfectionist; emotionally controlled; aware of social image and reputation.'),
            ('Factor Q4', 'Relaxed', 'Relaxed, tranquil, composed, low drive, satisfied; may lack motivation.',
             'Tense', 'Tense, frustrated, impatient, restless, hard-driving; highly stimulated but unable to discharge tension; may suffer from stress-related performance disruption.'),
        ]
        
        rows = []
        rows.append([
            Paragraph('Trait', header_style),
            Paragraph('Low score', header_style),
            Paragraph('High', header_style)
        ])
        
        for factor, low_title, low_desc, high_title, high_desc in factors_page2:
            low_cell = [Paragraph(f'<u>{low_title}</u>', title_style),
                       Paragraph(low_desc, desc_style)]
            high_cell = [Paragraph(f'<u>{high_title}</u>', title_style),
                        Paragraph(high_desc, desc_style)]
            
            low_table = Table([[p] for p in low_cell], colWidths=[col_widths[1] - 6])
            low_table.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER')]))
            
            high_table = Table([[p] for p in high_cell], colWidths=[col_widths[2] - 6])
            high_table.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER')]))
            
            rows.append([
                Paragraph(factor, trait_style),
                low_table,
                high_table
            ])
        
        table = Table(rows, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), GREEN_PRIMARY),
            ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ]))
        
        return table
    
    def _create_competency_descriptors_table(self, competencies):
        """Create competency descriptors table"""
        total_width = self.page_width - 2*self.margin
        
        name_style = ParagraphStyle('CompNameDesc', fontSize=10, fontName='Helvetica-Bold',
                                    textColor=GREEN_PRIMARY)
        desc_style = ParagraphStyle('CompDescText', fontSize=9, fontName='Helvetica-Oblique',
                                    textColor=colors.HexColor('#666666'), leading=12)
        
        rows = []
        for comp in competencies:
            name = comp.get('name', 'Unknown')
            description = comp.get('description', '')
            
            cell_content = []
            cell_content.append(Paragraph(name, name_style))
            if description:
                cell_content.append(Paragraph(description, desc_style))
            
            cell_table = Table([[p] for p in cell_content], colWidths=[total_width - 10])
            cell_table.setStyle(TableStyle([
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ]))
            
            rows.append([cell_table])
        
        table = Table(rows, colWidths=[total_width])
        table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F5F5F5')),
        ]))
        
        return table


def generate_roleplay_report(user_name, user_email, roleplay_name, scenario, 
                             overall_score, score_breakdown, interactions, 
                             completion_date=None, output_path=None,
                             cluster_name=None, client_logo_path=None,
                             personality_data=None, overall_role_fit=None,
                             play_id=None):
    """
    Generate a comprehensive Skills Gauge roleplay performance report
    
    Args:
        user_name: Name of the user
        user_email: Email of the user
        roleplay_name: Name of the roleplay scenario
        scenario: Description of the roleplay scenario
        overall_score: Overall performance score (0-100)
        score_breakdown: List of dicts with {name, score, total_possible, description}
        interactions: List of interaction dicts with user_text, response_text, and score
        completion_date: Date of completion (defaults to now)
        output_path: Path to save the PDF (defaults to temp folder)
        cluster_name: Name of the cluster (optional)
        client_logo_path: Path to client logo (optional)
        personality_data: 16PF personality analysis data (optional)
        overall_role_fit: Overall role fit percentage from 16PF analysis (optional)
        play_id: Play session ID for fetching 16PF data and time info (optional)
    
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
        output_path = os.path.join(temp_dir, f'skills_gauge_report_{user_email}_{timestamp}.pdf')
    
    # Initialize report generator
    report = SkillsGaugeReport(output_path)
    
    # Get cover image path
    from flask import current_app
    cover_image_path = os.path.join(current_app.root_path, 'static', 'images', 'report_cover_collage.png')
    
    # Get actual play time from database if play_id is provided
    actual_time_taken = "0Hr : 0Min"
    total_conversations = len(interactions) if interactions else 1
    attempted_conversations = total_conversations
    enable_16pf = False  # Default to disabled
    roleplay_id = None
    
    if play_id:
        try:
            from app.queries import get_play_info
            play_info = get_play_info(play_id)
            if play_info:
                # play table: id, start_time, end_time, user_id, roleplay_id, cluster_id, ...
                start_time = play_info[1] if len(play_info) > 1 else None
                end_time = play_info[2] if len(play_info) > 2 else None
                roleplay_id = play_info[4] if len(play_info) > 4 else None
                
                if start_time and end_time:
                    # Calculate actual time difference
                    if isinstance(start_time, str):
                        from datetime import datetime as dt
                        start_time = dt.strptime(start_time, '%Y-%m-%d %H:%M:%S')
                    if isinstance(end_time, str):
                        from datetime import datetime as dt
                        end_time = dt.strptime(end_time, '%Y-%m-%d %H:%M:%S')
                    
                    time_diff = end_time - start_time
                    total_seconds = int(time_diff.total_seconds())
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    actual_time_taken = f"{hours}Hr : {minutes:02d}Min"
                    print(f"[Report] Actual time taken: {actual_time_taken}")
        except Exception as e:
            print(f"[Report] Error getting play time: {str(e)}")
    
    # Check if 16PF analysis is enabled for this roleplay
    if play_id:
        try:
            import mysql.connector
            conn = mysql.connector.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                user=os.getenv('DB_USER', 'root'),
                password=os.getenv('DB_PASSWORD'),
                database=os.getenv('DB_NAME', 'roleplay')
            )
            cur = conn.cursor()
            
            # Get roleplay_id if not already set
            if not roleplay_id:
                cur.execute("SELECT roleplay_id FROM play WHERE id = %s", (play_id,))
                play_result = cur.fetchone()
                if play_result:
                    roleplay_id = play_result[0]
            
            # Check enable_16pf_analysis flag from roleplay_config
            if roleplay_id:
                cur.execute("""
                    SELECT enable_16pf_analysis FROM roleplay_config 
                    WHERE roleplay_id = %s
                """, (roleplay_id,))
                config_result = cur.fetchone()
                if config_result:
                    enable_16pf = bool(config_result[0])
                    print(f"[Report] 16PF analysis enabled: {enable_16pf}")
            
            cur.close()
            conn.close()
        except Exception as e:
            print(f"[Report] Error checking 16PF status: {str(e)}")
    
    # Get competency descriptions from master file if available
    competency_descriptions = {}
    if play_id:
        try:
            import mysql.connector
            conn = mysql.connector.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                user=os.getenv('DB_USER', 'root'),
                password=os.getenv('DB_PASSWORD'),
                database=os.getenv('DB_NAME', 'roleplay')
            )
            cur = conn.cursor()
            
            # Get roleplay_id from play
            if not roleplay_id:
                cur.execute("SELECT roleplay_id FROM play WHERE id = %s", (play_id,))
                play_result = cur.fetchone()
                if play_result:
                    roleplay_id = play_result[0]
            
            if roleplay_id:
                # Get competency file path
                cur.execute("SELECT competency_file_path FROM roleplay WHERE id = %s", (roleplay_id,))
                comp_result = cur.fetchone()
                if comp_result and comp_result[0]:
                    import pandas as pd
                    comp_file_path = os.path.abspath(comp_result[0])
                    if os.path.exists(comp_file_path):
                        comp_xls = pd.ExcelFile(comp_file_path)
                        comp_data = comp_xls.parse(0)
                        
                        # Build description mapping
                        name_col = None
                        desc_col = None
                        for col in comp_data.columns:
                            if 'competency' in col.lower() or 'name' in col.lower() or col == 'CompetencyType':
                                name_col = col
                            if 'description' in col.lower() or 'definition' in col.lower():
                                desc_col = col
                        
                        if name_col and desc_col:
                            for _, row in comp_data.iterrows():
                                name = row.get(name_col)
                                desc = row.get(desc_col)
                                if pd.notna(name) and pd.notna(desc):
                                    competency_descriptions[str(name).strip()] = str(desc).strip()
                        print(f"[Report] Loaded {len(competency_descriptions)} competency descriptions")
            
            cur.close()
            conn.close()
        except Exception as e:
            print(f"[Report] Error loading competency descriptions: {str(e)}")
    
    if completion_date is None:
        completion_date = datetime.now()
    
    if output_path is None:
        from flask import current_app
        temp_dir = os.path.join(current_app.root_path, 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = os.path.join(temp_dir, f'skills_gauge_report_{user_email}_{timestamp}.pdf')
    
    # Initialize report generator
    report = SkillsGaugeReport(output_path)
    
    # Get cover image path
    from flask import current_app
    cover_image_path = os.path.join(current_app.root_path, 'static', 'images', 'report_cover_collage.png')
    
    # Create callback for cover page (first page)
    def draw_cover_page(canvas, doc):
        report.draw_cover_page(canvas, doc, user_name, completion_date, cover_image_path, client_logo_path)
    
    def draw_later_pages(canvas, doc):
        # Add page number at the bottom center (page 2 onwards, so we show doc.page which starts from 1)
        page_num = doc.page
        page_width, page_height = A4
        
        # Draw page number in a green circle at bottom center
        canvas.saveState()
        
        # Green circle background
        circle_x = page_width / 2
        circle_y = 0.3 * inch
        circle_radius = 12
        
        canvas.setFillColor(GREEN_PRIMARY)
        canvas.circle(circle_x, circle_y, circle_radius, fill=True, stroke=False)
        
        # Page number text (white)
        canvas.setFillColor(WHITE)
        canvas.setFont('Helvetica-Bold', 10)
        canvas.drawCentredString(circle_x, circle_y - 4, str(page_num))
        
        canvas.restoreState()
    
    # Create the PDF document with custom page templates
    page_width, page_height = A4
    
    # Frame for cover page - full page (no content, all drawn on canvas)
    cover_frame = Frame(0, 0, page_width, page_height, id='cover')
    
    # Frame for content pages - with margins
    content_frame = Frame(0.5*inch, 0.4*inch, 
                         page_width - 1*inch, page_height - 0.8*inch,
                         id='content')
    
    # Create page templates
    cover_template = PageTemplate(id='Cover', frames=[cover_frame], onPage=draw_cover_page)
    content_template = PageTemplate(id='Content', frames=[content_frame], onPage=draw_later_pages)
    
    # Create document - start with Cover template
    doc = BaseDocTemplate(output_path, pagesize=A4)
    doc.addPageTemplates([cover_template, content_template])
    
    # Container for all elements
    all_elements = []
    
    # 1. Cover Page - The first page uses Cover template, then we switch to Content
    # We need a tiny spacer to fill the cover frame, then switch template and page break
    all_elements.append(Spacer(1, 1))  # Minimal spacer to use the cover frame
    all_elements.append(NextPageTemplate('Content'))  # Switch to content template for next page
    all_elements.append(PageBreak())
    
    # 2. Activity Summary Page
    # Use actual time taken from play session
    # Build activities list based on whether 16PF is enabled
    activities = []
    
    if enable_16pf:
        activities.append({
            'name': '16PF Trait\nAssessment',
            'icon': 'meeting.png',
            'time_available': '1Hr : 39Min',
            'time_taken': actual_time_taken  # Use same time as test (recording during roleplay)
        })
    
    activities.append({
        'name': 'Critical\nConversations (AI)',
        'icon': 'live-chat.png',
        'time_available': '1Hr : 39Min',
        'time_taken': actual_time_taken  # Use actual recorded time
    })
    
    all_elements.extend(report.generate_activity_summary_page(
        activities=activities,
        total_time_available='5Hr : 50Min' if enable_16pf else '1Hr : 39Min',
        total_time_taken=actual_time_taken,  # Use actual recorded time
        client_logo_path=client_logo_path
    ))
    
    # 3. Personality Fit Page (with 16PF data if available) - ONLY if 16PF is enabled
    pf16_personality_data = personality_data
    pf16_role_fit = overall_role_fit
    pf16_analysis_available = False  # Track if we have real 16PF data
    
    if enable_16pf:
        # Try to fetch 16PF data if play_id is provided and no personality data passed
        if play_id and not personality_data:
            try:
                from app.queries import get_16pf_analysis_by_play_id
                pf16_result = get_16pf_analysis_by_play_id(play_id)
                
                if pf16_result and pf16_result.get('status') == 'completed':
                    # Get personality scores from DB result
                    personality_scores = pf16_result.get('personality_scores', {})
                    
                    # Only use data if we actually have personality scores
                    if personality_scores and len(personality_scores) > 0:
                        # Convert to full 16PF display format with all 16 traits
                        pf16_personality_data = convert_personality_data_to_16pf_format(personality_scores)
                        pf16_role_fit = pf16_result.get('overall_role_fit')
                        pf16_analysis_available = True
                        print(f"[Report] Loaded 16PF data for play_id {play_id}: {len(pf16_personality_data)} traits")
                    else:
                        print(f"[Report] 16PF analysis completed but no personality scores found for play_id {play_id}")
                elif pf16_result and pf16_result.get('status') == 'failed':
                    print(f"[Report] 16PF analysis failed for play_id {play_id}: {pf16_result.get('error_message', 'Unknown error')}")
                elif pf16_result and pf16_result.get('status') == 'pending':
                    print(f"[Report] 16PF analysis still pending for play_id {play_id}")
                else:
                    print(f"[Report] No 16PF analysis found for play_id {play_id}")
            except Exception as e:
                print(f"[Report] Error loading 16PF data: {str(e)}")
        elif personality_data:
            # If personality_data was passed but is in simple format, convert it
            if personality_data and isinstance(personality_data, list) and len(personality_data) > 0:
                first_item = personality_data[0]
                if 'left_name' not in first_item and 'name' in first_item:
                    # Simple format - convert to full format
                    scores_dict = {item.get('name'): item.get('score', 5) for item in personality_data}
                    pf16_personality_data = convert_personality_data_to_16pf_format(scores_dict)
                    pf16_analysis_available = True
                else:
                    pf16_analysis_available = True
        
        
        # Add Personality Fit page only if 16PF is enabled AND we have real data
        if pf16_analysis_available and pf16_personality_data:
            all_elements.extend(report.generate_personality_fit_page(
                personality_data=pf16_personality_data,
                overall_role_fit=pf16_role_fit,
                client_logo_path=client_logo_path
            ))
        else:
            print(f"[Report] Skipping 16PF Personality Fit page - no valid analysis data available")
    
    # 4. Competency Score by Cluster
    # Convert score_breakdown to competencies format
    competencies = []
    overused = []
    
    for item in score_breakdown:
        name = item.get('name', 'Unknown')
        score = item.get('score', 0)
        total = item.get('total_possible', 3)
        
        # Calculate percentage
        percentage = (score / total * 100) if total > 0 else 0
        
        # Get description from master file or use provided description
        description = item.get('description', '')
        if not description and name in competency_descriptions:
            description = competency_descriptions[name]
        # Also try partial match for description
        if not description:
            for comp_name, comp_desc in competency_descriptions.items():
                if comp_name.lower() in name.lower() or name.lower() in comp_name.lower():
                    description = comp_desc
                    break
        
        comp = {
            'name': name,
            'description': description,
            'score': percentage,
            'target': 60,  # Default target
            'raw_score': score,  # Keep raw score for overused check
            'max_score': total
        }
        competencies.append(comp)
        
        # Check for overused (score > max expected) - must be strictly greater than
        if score > total:
            overused.append({
                'name': name,
                'score': score,
                'max_score': total
            })
    
    cluster_display_name = cluster_name if cluster_name else roleplay_name
    
    # Calculate a feedback score based on overall performance
    feedback_score = min(5, max(1, int(overall_score / 20)))  # 1-5 based on score
    
    # Activity stats for Critical Conversations section
    cluster_activity_stats = {
        'total': total_conversations,
        'attempted': attempted_conversations,
        'time_available': '1Hr : 39Min',
        'time_taken': actual_time_taken
    }
    
    all_elements.extend(report.generate_cluster_score_page(
        cluster_name=cluster_display_name,
        cluster_score=overall_score,
        competencies=competencies,
        overused_competencies=overused if overused else None,
        client_logo_path=client_logo_path,
        feedback_name='Feedback (Basic)',
        feedback_score=feedback_score,
        feedback_max=3,
        activity_stats=cluster_activity_stats
    ))
    
    # 5. Competency Score by Activity (Roleplays)
    # Use actual conversation stats
    activity_stats = {
        'total': total_conversations,
        'attempted': attempted_conversations,
        'time_available': '1Hr : 39Min',
        'time_taken': actual_time_taken  # Use actual recorded time
    }
    
    all_elements.extend(report.generate_activity_score_page(
        activity_name='Critical Conversations',
        activity_stats=activity_stats,
        topic_name='Roleplays',
        topic_score=overall_score,
        competencies=competencies,
        overused_competencies=overused if overused else None,
        client_logo_path=client_logo_path,
        feedback_name='Feedback (Basic)',
        feedback_score=feedback_score,
        feedback_max=3
    ))
    
    # 6. Competency Descriptors pages
    # Include 16PF descriptors only if 16PF is enabled AND we have valid data
    all_elements.extend(report.generate_competency_descriptors_page(
        competencies=competencies,
        client_logo_path=client_logo_path,
        include_16pf=enable_16pf and pf16_analysis_available,
        personality_data=pf16_personality_data if pf16_analysis_available else None
    ))
    
    # Build PDF
    doc.build(all_elements)
    
    print(f"Skills Gauge Report generated: {output_path}")
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
