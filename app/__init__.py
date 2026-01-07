from flask import Flask
from config import Config
from werkzeug.routing import IntegerConverter
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

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

# Session configuration - keep users logged in
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = True  # Make session permanent (survives browser close)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)  # Session lasts 7 days
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_KEY_PREFIX'] = 'rolevo:'

from app import routes, models, errors, queries


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

app.jinja_env.filters['split'] = jinja_split