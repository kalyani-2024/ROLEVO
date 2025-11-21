# Quick Start Guide - Report System

## ⚡ 5-Minute Setup

### Step 1: Package Already Installed ✅
```bash
# reportlab is already installed
pip show reportlab
```

### Step 2: Configure Email (Choose One)

#### Option A: Gmail (Recommended)
1. Go to: https://myaccount.google.com/apppasswords
2. Create app password for "Mail"
3. Add to `.env`:
```env
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-16-char-app-password
ADMIN_EMAIL=your-email@gmail.com
ADMIN_NAME=Your Name
```

#### Option B: Outlook
```env
SMTP_SERVER=smtp.office365.com
SMTP_PORT=587
SMTP_USERNAME=your-email@outlook.com
SMTP_PASSWORD=your-password
ADMIN_EMAIL=your-email@outlook.com
ADMIN_NAME=Your Name
```

### Step 3: Restart Flask
```bash
python roleplay.py
```

### Step 4: Test It!
1. Complete any roleplay as a user
2. Watch console for: `"Started background report generation for play_id X"`
3. Check email inbox for report
4. Find PDF in `app/temp/` folder

## 🎯 That's It!

Reports are now automatically sent after every roleplay completion!

## 📧 Email Example

**To:** user@example.com  
**Subject:** Your Rolevo Performance Report - [Roleplay Name]  
**Attachment:** report_user@example.com_20251121_143052.pdf  

## 🔧 Troubleshooting

**No email received?**
- Check spam folder
- Verify SMTP credentials in `.env`
- Check console for errors

**Permission denied errors?**
- Gmail: Use App Password (not regular password)
- Enable "Less secure apps" if needed

**PDF not generated?**
- Check `app/temp/` folder exists
- Verify reportlab: `pip show reportlab`

## 📱 Support

For detailed documentation, see:
- `REPORT_SYSTEM_README.md` - Full documentation
- `EMAIL_SETUP.txt` - Email configuration details
- `IMPLEMENTATION_SUMMARY.md` - What was built

---
**Ready to Go!** 🚀
