#!/usr/bin/env python3
"""
Batch generate TTS audio for 7 male and 7 female voices using app.tts_service

Usage:
  - Set ELEVENLABS_API_KEY (or XI_API_KEY) in your environment.
  - Run: python scripts/generate_batch_tts.py

This will write MP3 files to ./static/generated_tts/
"""
import os
import sys
from pathlib import Path

# Add project root to path so we can import app.tts_service
PROJECT_ROOT = Path(__file__).resolve().parents[1]
import importlib.util
tts_path = PROJECT_ROOT / 'app' / 'tts_service.py'
spec = importlib.util.spec_from_file_location('tts_service', str(tts_path))
tts_service = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tts_service)


def load_dotenv_file(path: Path):
    """Load simple KEY=VALUE pairs from a .env file into os.environ.

    This is a minimal loader (no sections, no export/quotes parsing beyond stripping).
    """
    try:
        if not path.exists():
            return
        with path.open('r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' not in line:
                    continue
                key, val = line.split('=', 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                # Do not override existing environment variables
                if key not in os.environ:
                    os.environ[key] = val
    except Exception as e:
        print(f"Warning: failed to load .env file: {e}")


def main():
    api_key = os.getenv('ELEVENLABS_API_KEY') or os.getenv('XI_API_KEY')
    if not api_key:
        print("ERROR: ELEVENLABS_API_KEY or XI_API_KEY not set in environment")
        return

    out_dir = PROJECT_ROOT / 'static' / 'generated_tts'
    out_dir.mkdir(parents=True, exist_ok=True)

    voices = tts_service.OPENAI_VOICES

    male_list = [name for name, info in voices.items() if info.get('gender') == 'male']
    female_list = [name for name, info in voices.items() if info.get('gender') == 'female' and not str(info.get('voice_id','')).startswith('PLACEHOLDER')]

    if len(male_list) < 7:
        print(f"Warning: only {len(male_list)} male voices available; will generate for all available.")
    if len(female_list) < 7:
        print(f"Warning: only {len(female_list)} female voices available; will generate for all available.")

    male_sel = male_list[:7]
    female_sel = female_list[:7]

    print(f"Selected {len(male_sel)} male and {len(female_sel)} female voices.")

    sample_male = "Hello, this is a sample male voice for testing. This is a short test phrase."
    sample_female = "Hello, this is a sample female voice for testing. This is a short test phrase."

    results = []

    # generate for male then female
    for name in male_sel + female_sel:
        text = sample_male if name in male_sel else sample_female
        safe_name = name.replace(' ', '_')
        out_path = out_dir / f"{safe_name}.mp3"
        try:
            print(f"Generating -> {name} -> {out_path}")
            tts_service.generate_tts(text, name, str(out_path))
            results.append((name, True, str(out_path)))
        except Exception as e:
            print(f"Error generating {name}: {e}")
            results.append((name, False, str(e)))

    print("\nSummary:")
    for name, ok, info in results:
        status = 'OK' if ok else 'ERROR'
        print(f"- {name}: {status} -> {info}")


if __name__ == '__main__':
    main()
