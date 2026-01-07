"""
Test Script for Report System
Run this to test report generation without needing a full roleplay session
"""

from app.report_generator import generate_roleplay_report
from app.email_service import send_report_email
import os
from datetime import datetime

def test_report_generation():
    """Test PDF generation"""
    print("Testing PDF report generation...")
    
    # Sample data
    user_name = "Test User"
    user_email = "test@example.com"
    roleplay_name = "Manager Performance Review"
    scenario = "You are a manager at a BPO and lead a team of processors. One of your processors, Sheela, has been on your team for six years."
    overall_score = 85
    score_breakdown = {
        "Communication": 90,
        "Empathy": 80,
        "Problem Solving": 85,
        "Active Listening": 88
    }
    interactions = [
        {
            "user_text": "Hi Sheela, thanks for meeting with me today.",
            "response_text": "Thank you for taking the time to discuss this."
        },
        {
            "user_text": "I wanted to talk about your recent request to change processes.",
            "response_text": "Yes, I appreciate you considering it."
        }
    ]
    
    try:
        report_path = generate_roleplay_report(
            user_name=user_name,
            user_email=user_email,
            roleplay_name=roleplay_name,
            scenario=scenario,
            overall_score=overall_score,
            score_breakdown=score_breakdown,
            interactions=interactions
        )
        
        print(f"✅ SUCCESS! Report generated at: {report_path}")
        print(f"File size: {os.path.getsize(report_path)} bytes")
        print(f"File exists: {os.path.exists(report_path)}")
        
        return report_path
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def test_email_sending(report_path, recipient_email):
    """Test email sending (requires SMTP configuration)"""
    print(f"\nTesting email sending to {recipient_email}...")
    
    if not report_path or not os.path.exists(report_path):
        print("❌ Cannot test email - report file not found")
        return False
    
    try:
        success = send_report_email(
            to_email=recipient_email,
            user_name="Test User",
            roleplay_name="Manager Performance Review",
            overall_score=85,
            report_pdf_path=report_path,
            admin_name="Test Admin"
        )
        
        if success:
            print(f"✅ SUCCESS! Email sent to {recipient_email}")
            print("Check your inbox (and spam folder)")
        else:
            print("❌ Email sending failed - check SMTP configuration")
            print("Add these to your .env file:")
            print("SMTP_SERVER=smtp.gmail.com")
            print("SMTP_PORT=587")
            print("SMTP_USERNAME=your-email@gmail.com")
            print("SMTP_PASSWORD=your-app-password")
        
        return success
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("ROLEVO REPORT SYSTEM TEST")
    print("=" * 60)
    
    # Test PDF generation
    report_path = test_report_generation()
    
    # Test email sending (optional)
    if report_path:
        test_email = input("\nEnter email address to test sending (or press Enter to skip): ").strip()
        
        if test_email:
            test_email_sending(report_path, test_email)
        else:
            print("\nSkipping email test. To test later:")
            print(f"1. Configure SMTP in .env")
            print(f"2. Run: python test_report_system.py")
    
    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)
