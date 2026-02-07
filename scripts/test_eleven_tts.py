import os
import sys
import pathlib
# Ensure project root is on sys.path so `import app` works
root = pathlib.Path(__file__).resolve().parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))
from app.tts_service import generate_elevenlabs_tts, ELEVENLABS_VOICES

output = 'test_eleven_output.mp3'
text = 'This is a short test from ElevenLabs integration.'

# pick a female voice if available, else any voice
voice = None
for name, info in ELEVENLABS_VOICES.items():
    if info.get('gender') == 'female':
        voice = name
        break
if not voice:
    voice = next(iter(ELEVENLABS_VOICES.keys()))

print('Using voice:', voice)

# Ensure API key present
if not os.getenv('ELEVENLABS_API_KEY'):
    # try to load from .env
    try:
        with open('.env','r',encoding='utf-8') as f:
            for line in f:
                if line.startswith('ELEVENLABS_API_KEY='):
                    os.environ['ELEVENLABS_API_KEY'] = line.split('=',1)[1].strip()
                    break
    except Exception:
        pass

if not os.getenv('ELEVENLABS_API_KEY'):
    print('ELEVENLABS_API_KEY not set; aborting test')
    raise SystemExit(1)

ok = generate_elevenlabs_tts(text, voice, output)
print('Generated:', ok)
print('Saved to', output)
