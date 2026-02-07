import os, traceback
from pathlib import Path
import importlib.util

# Load OPENAI_API_KEY from .env if present
env_path = Path('.env')
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line.startswith('OPENAI_API_KEY='):
            val = line.split('=',1)[1].strip()
            os.environ.setdefault('OPENAI_API_KEY', val)
            break

print('OPENAI_API_KEY present:', bool(os.getenv('OPENAI_API_KEY')))

# Load tts_service by path to avoid importing Flask app package
tts_path = Path('app') / 'tts_service.py'
spec = importlib.util.spec_from_file_location('tts_service_local', str(tts_path))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

out_dir = Path('app') / 'temp'
out_dir.mkdir(parents=True, exist_ok=True)
out_file = out_dir / 'openai_tts_test.mp3'

try:
    print('Calling generate_openai_tts...')
    ok = module.generate_openai_tts('Assistant test phrase for OpenAI TTS.', 'echo', str(out_file))
    print('generate_openai_tts returned:', ok)
except Exception as e:
    print('Exception when generating TTS:')
    traceback.print_exc()

print('Output path:', out_file)
print('Exists:', out_file.exists())
if out_file.exists():
    print('Size (bytes):', out_file.stat().st_size)
