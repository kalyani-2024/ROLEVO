# Roleplay Performance Report System

## Overview
The system automatically generates PDF performance reports and sends them via email to users after they complete a roleplay session.

## Features

### 1. Automatic Report Generation
- Triggered automatically when a roleplay session is completed
- Runs in background thread to avoid blocking the application
- Generates professional PDF reports with:
  - User information and completion date
  - Scenario description
  - Overall performance score (color-coded)
  - Detailed score breakdown by competency
  - Complete interaction transcript
  - Personalized recommendations for improvement

### 2. Email Delivery
- Reports are automatically emailed to the user's registered email address
- Email includes performance summary and PDF attachment
- Configurable SMTP settings for different email providers

### 3. Manual Report Sending (Admin)
- Admins can manually trigger report generation and sending
- Route: `/admin/send_report/<play_id>` (POST request)
- Useful for resending reports or generating reports for older sessions

## Setup Instructions

### 1. Install Required Package
```bash
pip install reportlab
```

### 2. Configure Email Settings
Add the following to your `.env` file:

```env
# SMTP Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Admin Email
ADMIN_EMAIL=admin@yourcompany.com
ADMIN_NAME=Rolevo Admin
```

### 3. Gmail Setup (Recommended)
1. Go to your Google Account settings
2. Navigate to Security > 2-Step Verification
3. Scroll to "App passwords"
4. Generate a new app password for "Mail"
5. Use this password in the `SMTP_PASSWORD` field

### 4. Test the System
1. Complete a roleplay session
2. Check the console for: `"Started background report generation for play_id X"`
3. Report PDF will be saved in `app/temp/` folder
4. Email will be sent to the user's registered email

## File Structure

```
app/
├── report_generator.py     # PDF generation logic
├── email_service.py        # Email sending functionality
├── routes.py              # Updated with report routes
└── temp/                  # Generated PDF reports stored here
```

## Usage

### Automatic (Default Behavior)
Reports are automatically generated and sent when:
- User completes a roleplay session
- `post_attempt_data()` function is called
- Scores are calculated and saved

### Manual (Admin Interface)
To manually send a report:
1. Get the `play_id` from the database
2. Make a POST request to `/admin/send_report/<play_id>`
3. Or add a "Send Report" button in the admin interface

Example button in admin template:
```html
<form method="POST" action="{{ url_for('admin_send_report', play_id=play.id) }}">
    <button type="submit" class="btn btn-primary">Send Report</button>
</form>
```

## Customization

### Report Styling
Edit `app/report_generator.py`:
- `title_style`: Report title formatting
- `heading_style`: Section headings
- `get_score_color()`: Score color thresholds
- `get_rating_text()`: Performance ratings
- `generate_recommendations()`: Custom feedback logic

### Email Templates
Edit `app/email_service.py`:
- `send_report_email()`: Main email body
- `get_performance_level()`: Performance level text

## Troubleshooting

### Reports Not Sending
1. Check console for error messages
2. Verify SMTP credentials in `.env`
3. Ensure `reportlab` is installed
4. Check email spam folder

### PDF Generation Errors
- Ensure `app/temp/` directory exists and is writable
- Check for missing score data in database
- Verify all required fields are populated

### Email Authentication Errors
- Gmail: Use App Password, not regular password
- Outlook: Enable SMTP in account settings
- Check firewall/antivirus blocking port 587

## Database Requirements

The system uses existing tables:
- `user`: User email addresses
- `play`: Roleplay session data
- `scoremaster`: Overall scores
- `scorebreakdown`: Individual competency scores
- `chathistory`: Interaction transcript

No additional database changes required.

## API Reference

### `generate_roleplay_report()`
Generates PDF report.

**Parameters:**
- `user_name`: User's name
- `user_email`: User's email
- `roleplay_name`: Roleplay scenario name
- `scenario`: Scenario description
- `overall_score`: Overall score (0-100)
- `score_breakdown`: Dict of competency scores
- `interactions`: List of interaction dicts
- `completion_date`: Optional completion date
- `output_path`: Optional custom output path

**Returns:** Path to generated PDF

### `send_report_email()`
Sends email with report attachment.

**Parameters:**
- `to_email`: Recipient email
- `user_name`: User's name
- `roleplay_name`: Roleplay scenario name
- `overall_score`: Overall score
- `report_pdf_path`: Path to PDF file
- `admin_email`: Optional sender email
- `admin_name`: Optional sender name

**Returns:** Boolean (success/failure)

### `generate_and_send_report_async()`
Background function to generate and send report.

**Parameters:**
- `play_id`: Database play session ID

**Returns:** Boolean (success/failure)

## Security Notes

- Never commit `.env` file with real credentials
- Use app passwords, not account passwords
- Restrict admin routes to authenticated users only
- PDF files in `temp/` folder should be periodically cleaned
- Consider encrypting email credentials in production

## Future Enhancements

- [ ] HTML email templates with inline images
- [ ] Configurable report templates
- [ ] Scheduled batch report sending
- [ ] Report analytics dashboard
- [ ] Multi-language report support
- [ ] Export to other formats (Word, CSV)
- [ ] Email delivery tracking
