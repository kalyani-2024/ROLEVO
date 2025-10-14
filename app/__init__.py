from flask import Flask
from config import Config
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config.from_object(Config)

app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Add these configurations
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY')

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