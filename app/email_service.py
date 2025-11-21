"""
Email Service Module for Rolevo
Handles sending emails with reports and notifications
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os


def send_report_email(to_email, user_name, roleplay_name, overall_score, 
                     report_pdf_path, admin_email=None, admin_name="Rolevo Admin"):
    """
    Send roleplay performance report via email
    
    Args:
        to_email: Recipient email address
        user_name: Name of the user
        roleplay_name: Name of the roleplay scenario
        overall_score: Overall performance score
        report_pdf_path: Path to the PDF report file
        admin_email: Admin's email (sender)
        admin_name: Admin's name
    
    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        # Email configuration - should be in environment variables
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        smtp_username = os.getenv('SMTP_USERNAME', admin_email)
        smtp_password = os.getenv('SMTP_PASSWORD', '')
        
        if not smtp_username or not smtp_password:
            print("Error: SMTP credentials not configured")
            return False
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = f"{admin_name} <{smtp_username}>"
        msg['To'] = to_email
        msg['Subject'] = f"Your Rolevo Performance Report - {roleplay_name}"
        
        # Email body
        performance_level = get_performance_level(overall_score)
        
        body = f"""
Dear {user_name},

Thank you for completing the roleplay scenario: "{roleplay_name}".

Your overall performance score: {overall_score}/100 ({performance_level})

Please find attached your detailed performance report. This report includes:
- Overall performance summary
- Detailed score breakdown by criteria
- Complete interaction transcript
- Personalized recommendations for improvement

We encourage you to review the report carefully and use the feedback to enhance your skills.

If you have any questions or would like to discuss your performance, please don't hesitate to reach out.

Best regards,
{admin_name}
Rolevo Team

---
This is an automated message. Please do not reply to this email.
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Attach PDF report
        if os.path.exists(report_pdf_path):
            with open(report_pdf_path, 'rb') as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                
                filename = os.path.basename(report_pdf_path)
                part.add_header('Content-Disposition', f'attachment; filename= {filename}')
                msg.attach(part)
        else:
            print(f"Warning: Report file not found at {report_pdf_path}")
            return False
        
        # Send email
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_username, smtp_password)
        text = msg.as_string()
        server.sendmail(smtp_username, to_email, text)
        server.quit()
        
        print(f"Report email sent successfully to {to_email}")
        return True
        
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False


def send_completion_notification(to_email, user_name, roleplay_name, cluster_name=None):
    """
    Send a simple completion notification email
    
    Args:
        to_email: Recipient email address
        user_name: Name of the user
        roleplay_name: Name of the roleplay scenario
        cluster_name: Optional cluster name
    
    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        smtp_username = os.getenv('SMTP_USERNAME')
        smtp_password = os.getenv('SMTP_PASSWORD')
        
        if not smtp_username or not smtp_password:
            print("Error: SMTP credentials not configured")
            return False
        
        msg = MIMEMultipart()
        msg['From'] = f"Rolevo <{smtp_username}>"
        msg['To'] = to_email
        msg['Subject'] = f"Roleplay Completed - {roleplay_name}"
        
        cluster_info = f" in {cluster_name}" if cluster_name else ""
        
        body = f"""
Dear {user_name},

Congratulations on completing the roleplay scenario: "{roleplay_name}"{cluster_info}!

Your performance is being evaluated and you will receive a detailed report shortly.

Keep up the great work!

Best regards,
Rolevo Team
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_username, smtp_password)
        text = msg.as_string()
        server.sendmail(smtp_username, to_email, text)
        server.quit()
        
        print(f"Completion notification sent to {to_email}")
        return True
        
    except Exception as e:
        print(f"Error sending notification: {str(e)}")
        return False


def get_performance_level(score):
    """Return performance level text based on score"""
    if score >= 90:
        return 'Outstanding'
    elif score >= 80:
        return 'Excellent'
    elif score >= 70:
        return 'Very Good'
    elif score >= 60:
        return 'Good'
    elif score >= 50:
        return 'Satisfactory'
    else:
        return 'Needs Improvement'
