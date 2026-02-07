from flask import Flask
from config import Config
from werkzeug.routing import IntegerConverter
import os
import re
from datetime import timedelta, datetime, timezone
from dotenv import load_dotenv

load_dotenv()

# IST Timezone (UTC+5:30) - India Standard Time
IST = timezone(timedelta(hours=5, minutes=30))
# Database server timezone (UTC+0) - PythonAnywhere uses UTC
DB_SERVER_TZ = timezone(timedelta(hours=0))

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
                return dt  # Return as-is if parsing fails
    
    if not isinstance(dt, datetime):
        return dt
    
    if dt.tzinfo is None:
        # Naive datetime from database - it's in DB server timezone (UTC+4)
        # Attach the DB server timezone, then convert to IST
        dt = dt.replace(tzinfo=DB_SERVER_TZ)
    
    # Convert to IST
    return dt.astimezone(IST)

# Custom URL converter to handle signed integers (including negative like -1)
class SignedIntConverter(IntegerConverter):
    regex = r'-?\d+'

app = Flask(__name__)
app.url_map.converters['signed_int'] = SignedIntConverter
app.config.from_object(Config)

app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Add these configurations
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY')

# Session configuration - keep users logged in even after closing browser tab
app.config['SESSION_PERMANENT'] = True  # Make session permanent (survives browser close)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)  # Session lasts 30 days
app.config['SESSION_REFRESH_EACH_REQUEST'] = True  # Refresh session on each request to extend lifetime

# Cookie settings - these are critical for persistence across browser sessions
# Auto-enable secure cookies in production (when FLASK_ENV=production)
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production'
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent JavaScript access
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Prevent CSRF while allowing normal navigation
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=30)  # Remember me duration

# CSRF Protection - enable globally
from flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect()
csrf.init_app(app)

# Rate Limiting - protect against brute force attacks
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"],
        storage_uri="memory://",
    )
except ImportError:
    # Flask-Limiter not installed - create a dummy limiter
    print("WARNING: Flask-Limiter not installed. Rate limiting disabled.")
    class DummyLimiter:
        def limit(self, *args, **kwargs):
            def decorator(f):
                return f
            return decorator
    limiter = DummyLimiter()

from app import routes, models, errors, queries, api_integration


# Register custom Jinja filters
def jinja_split(value, sep=','):
	"""Split a string by sep and trim whitespace. Returns empty list for None/empty."""
	if value is None:
		return []
	try:
		# If value is JSON list like ["English","Hindi"], it's already been handled by template replace
		parts = [p.strip() for p in str(value).split(sep) if p.strip()]
		return parts
	except Exception:
		return []

def jinja_ist_format(value, fmt='%b %d, %Y %I:%M %p IST'):
	"""Format a datetime in IST timezone"""
	if value is None:
		return 'N/A'
	try:
		ist_dt = convert_to_ist(value)
		if ist_dt:
			return ist_dt.strftime(fmt)
		return str(value)
	except Exception:
		return str(value)

app.jinja_env.filters['split'] = jinja_split
app.jinja_env.filters['ist'] = jinja_ist_format


def jinja_basename(value):
    """Return the original uploaded filename from a path.
    
    Handles patterns like:
    - Full paths: extracts basename first
    - temp_123_456_originalname.ext -> originalname.ext
    - RP_ABC123_456_originalname.ext -> originalname.ext  
    - ID_123_originalname.ext -> originalname.ext
    - Old pattern: ID_competency.xlsx -> competency file (no original name available)
    """
    if not value:
        return ''
    try:
        # Get basename first (removes directory path)
        name = os.path.basename(str(value))
        
        # Pattern: prefix_TIMESTAMP_originalname.ext
        # Examples: temp_123_456_myfile.xls, RP_ABC_123_myfile.xlsx
        # Match anything up to and including a timestamp, then capture the rest
        match = re.match(r'^[A-Za-z0-9_]+_\d+_(.+)$', name)
        if match:
            return match.group(1)
        
        # Old pattern for competency files: ID_competency.xlsx (no original name)
        if name.endswith('_competency.xlsx'):
            return 'competency file'
        
        # No pattern matched, return filename as-is
        return name
    except Exception:
        return str(value)


app.jinja_env.filters['basename'] = jinja_basename