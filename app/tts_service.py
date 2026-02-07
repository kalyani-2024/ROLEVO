"""
Text-to-Speech Service using AWS Polly.
Replaces OpenAI TTS with AWS Polly Neural voices.
Enforces strict gender matching, unique voice assignment, and Indian English for specific languages.
"""

import os
import random
import json
import hashlib
from typing import List, Dict, Optional
import shutil
import boto3
from botocore.exceptions import BotoCoreError, ClientError

# AWS Polly Client (initialized lazily)
_polly_client = None

def get_polly_client():
    global _polly_client
    if not _polly_client:
        # Expects AWS credentials in environment variables:
        # AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION
        region = os.getenv('AWS_REGION', 'us-east-1')
        _polly_client = boto3.client('polly', region_name=region)
    return _polly_client

def debug_log(msg: str):
    # Minimal debug logging
    try:
        print(f"[TTS] {msg}")
    except Exception:
        pass

# --- Voice Configuration ---

# AWS Polly Neural Voices
# We categorize them by Gender and Locale.
# For Indian languages, we prefer 'en-IN' voices.

POLLY_VOICES_METADATA = {
    # --- US English (en-US) - Neural (Adult Voices Only) ---
    'Joanna': {'gender': 'female', 'language': 'en-US', 'engine': 'neural', 'description': 'Female, US, Neural'},
    'Salli': {'gender': 'female', 'language': 'en-US', 'engine': 'neural', 'description': 'Female, US, Neural'},
    'Kendra': {'gender': 'female', 'language': 'en-US', 'engine': 'neural', 'description': 'Female, US, Neural'},
    'Kimberly': {'gender': 'female', 'language': 'en-US', 'engine': 'neural', 'description': 'Female, US, Neural'},
    'Danielle': {'gender': 'female', 'language': 'en-US', 'engine': 'neural', 'description': 'Female, US, Neural'},
    'Ruth': {'gender': 'female', 'language': 'en-US', 'engine': 'neural', 'description': 'Female, US, Neural'},
    
    'Matthew': {'gender': 'male', 'language': 'en-US', 'engine': 'neural', 'description': 'Male, US, Neural'},
    'Joey': {'gender': 'male', 'language': 'en-US', 'engine': 'neural', 'description': 'Male, US, Neural'},
    'Stephen': {'gender': 'male', 'language': 'en-US', 'engine': 'neural', 'description': 'Male, US, Neural'},
    # Note: Removed child voices: Justin, Kevin (male children), Ivy (female child)
    
    # --- Indian English (en-IN) - Neural/Standard ---
    'Kajal': {'gender': 'female', 'language': 'en-IN', 'engine': 'neural', 'description': 'Female, Indian English, Neural'},
    'Aditi': {'gender': 'female', 'language': 'en-IN', 'engine': 'standard', 'description': 'Female, Indian English/Hindi, Standard'}, # Aditi is standard only? Checking support.
    # Raveena is also en-IN female (Standard)
    'Raveena': {'gender': 'female', 'language': 'en-IN', 'engine': 'standard', 'description': 'Female, Indian English, Standard'},

    # --- British English (en-GB) - Neural (Good fallback for variety) ---
    'Amy': {'gender': 'female', 'language': 'en-GB', 'engine': 'neural', 'description': 'Female, British, Neural'},
    'Emma': {'gender': 'female', 'language': 'en-GB', 'engine': 'neural', 'description': 'Female, British, Neural'}, 
    'Brian': {'gender': 'male', 'language': 'en-GB', 'engine': 'neural', 'description': 'Male, British, Neural'},
    'Arthur': {'gender': 'male', 'language': 'en-GB', 'engine': 'neural', 'description': 'Male, British, Neural'},

    # --- French (fr-FR, fr-CA, fr-BE) --- 
    # Total 8 voices found
    'Léa': {'gender': 'female', 'language': 'fr-FR', 'engine': 'neural', 'description': 'Female, French, Neural'},
    'Rémi': {'gender': 'male', 'language': 'fr-FR', 'engine': 'neural', 'description': 'Male, French, Neural'},
    'Gabrielle': {'gender': 'female', 'language': 'fr-CA', 'engine': 'neural', 'description': 'Female, Canadian French, Neural'},
    'Liam': {'gender': 'male', 'language': 'fr-CA', 'engine': 'neural', 'description': 'Male, Canadian French, Neural'},
    'Isabelle': {'gender': 'female', 'language': 'fr-BE', 'engine': 'neural', 'description': 'Female, Belgian French, Neural'},
    # Standard-only or Generative-only that falls back to Standard if Neural not listed explicitly as primary?
    # Polly Check showed: Céline ['generative', 'standard'], Mathieu ['standard'], Chantal ['standard']
    'Céline': {'gender': 'female', 'language': 'fr-FR', 'engine': 'standard', 'description': 'Female, French, Standard'},
    'Mathieu': {'gender': 'male', 'language': 'fr-FR', 'engine': 'standard', 'description': 'Male, French, Standard'},
    'Chantal': {'gender': 'female', 'language': 'fr-CA', 'engine': 'standard', 'description': 'Female, Canadian French, Standard'},

    # --- Arabic (ar-AE, arb) ---
    # Total 3 voices found
    'Hala': {'gender': 'female', 'language': 'ar-AE', 'engine': 'neural', 'description': 'Female, Gulf Arabic, Neural'},
    'Zayd': {'gender': 'male', 'language': 'ar-AE', 'engine': 'neural', 'description': 'Male, Gulf Arabic, Neural'},
    'Zeina': {'gender': 'female', 'language': 'arb', 'engine': 'standard', 'description': 'Female, Modern Standard Arabic, Standard'},
}

# Indian languages triggering Indian English voices
INDIAN_LANGUAGES = {
    'Hindi', 'Tamil', 'Telugu', 'Kannada', 'Marathi', 'Bengali', 'Malayalam', 'Gujarati'
}

# Language code mapping for selection logic
# Maps incoming language name (from UI) to Polly LanguageCode prefix
LANGUAGE_MAPPING = {
    'French': 'fr',
    'Arabic': 'ar', # Matches ar-AE and arb (if we check startswith 'ar')
}

# Mapping of normalized character_name -> assigned voice name
SELECTED_VOICES: dict = {}

# Directory to store generated/cached TTS files
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DEFAULT_CACHE_DIR = os.path.join(BASE_DIR, 'static', 'generated_tts')
try:
    os.makedirs(DEFAULT_CACHE_DIR, exist_ok=True)
except Exception as e:
    print(f"[TTS] Warning: Could not create cache dir {DEFAULT_CACHE_DIR}: {e}")
    # Fallback to temp directory
    import tempfile
    DEFAULT_CACHE_DIR = os.path.join(tempfile.gettempdir(), 'rolevo_tts_cache')
    os.makedirs(DEFAULT_CACHE_DIR, exist_ok=True)

_SELECTED_VOICES_PATH = os.path.join(DEFAULT_CACHE_DIR, 'selected_voices.json')


def get_available_voices(language_code=None, gender=None):
    """Return list of available voices with metadata, optionally filtered."""
    voices = []
    for name, info in POLLY_VOICES_METADATA.items():
        if language_code and info['language'] != language_code:
            continue
        if gender and info['gender'] != gender.lower():
            continue
        
        voices.append({
            'name': name,
            'provider': 'polly',
            'voice_id': name,
            'gender': info['gender'],
            'language': info['language'],
            'description': info['description']
        })
    return voices


# --- Persistence Logic ---

def _load_selected_voices():
    global SELECTED_VOICES
    try:
        if os.path.exists(_SELECTED_VOICES_PATH):
            with open(_SELECTED_VOICES_PATH, 'r', encoding='utf-8') as fh:
                data = json.load(fh)
                if isinstance(data, dict):
                    SELECTED_VOICES.update({k: v for k, v in data.items()})
                    debug_log(f"Loaded {len(SELECTED_VOICES)} persisted voice assignments")
    except Exception as e:
        debug_log(f"Failed loading selected voices: {e}")

def _save_selected_voices():
    try:
        with open(_SELECTED_VOICES_PATH, 'w', encoding='utf-8') as fh:
            json.dump(SELECTED_VOICES, fh, ensure_ascii=False, indent=2)
    except Exception as e:
        debug_log(f"Failed saving selected voices: {e}")

_load_selected_voices()


# --- Assignment Logic ---

def select_voice_for_character(character_name: str, gender: str = 'female', language: str = 'English') -> str:
    """Select a unique voice for a character based on gender and language.
    
    Guarantees:
    1. Same character always gets same voice (if persisted).
    2. Prioritizes 'en-IN' voices if language is Indian.
    3. Tries to assign a voice that hasn't been used yet.
    4. Deterministic fallback if pool exhausted.
    """
    key = character_name.strip()
    
    # 1. Return existing assignment (check if it matches strict requirements? No, trust persistence for stability)
    # However, if language requirement changed (e.g. English -> Hindi), we might want to re-assign?
    # For now, stick to persistence to avoid voice switching mid-convo.
    if key in SELECTED_VOICES:
        return SELECTED_VOICES[key]
    
    normalized_gender = gender.lower() if gender else 'female'
    if normalized_gender not in ['male', 'female']:
        normalized_gender = 'female'
    

    # Determine required locale
    target_locale = 'en-US' # default
    is_indian_english = False
    
    # Check for Indian English
    if language in INDIAN_LANGUAGES:
        target_locale = 'en-IN'
        is_indian_english = True
    
    # Check for other mapped languages (prefix matching)
    language_prefix = LANGUAGE_MAPPING.get(language, 'en')
    
    # 2. Find available voices
    candidates = []
    
    if is_indian_english:
        # Primary search: Match gender AND specific Indian locale
        candidates = [
            name for name, info in POLLY_VOICES_METADATA.items() 
            if info['gender'] == normalized_gender and info['language'] == target_locale
        ]
        # Fallback to general English later if empty
    elif language_prefix != 'en':
        # For French/Arabic, match based on language prefix (fr-FR, fr-CA match 'fr')
        candidates = [
            name for name, info in POLLY_VOICES_METADATA.items() 
            if info['gender'] == normalized_gender and (
                info['language'].startswith(language_prefix) or 
                (language_prefix == 'ar' and info['language'] == 'arb') # Handle arb for Arabic
            )
        ]
    else:
        # Default English behavior (US preferred but not strict?)
        # Let's default to US for 'English'
        candidates = [
            name for name, info in POLLY_VOICES_METADATA.items() 
            if info['gender'] == normalized_gender and info['language'] == 'en-US'
        ]

    # Fallback 1: If no candidates for en-IN Male (very likely), use en-GB or en-US
    if not candidates and is_indian_english:
        debug_log(f"No {normalized_gender} voices for en-IN. Falling back to en-GB/en-US.")
        # Try GB first (often closer neutral accent than US)
        candidates = [
            name for name, info in POLLY_VOICES_METADATA.items() 
            if info['gender'] == normalized_gender and info['language'] == 'en-GB'
        ]
        if not candidates:
             candidates = [
                name for name, info in POLLY_VOICES_METADATA.items() 
                if info['gender'] == normalized_gender and info['language'] == 'en-US'
            ]
            
    # Fallback 2: General fallback (any voice of correct gender)
    if not candidates:
        candidates = [
            name for name, info in POLLY_VOICES_METADATA.items() 
            if info['gender'] == normalized_gender
        ]
        
    # 3. Find confirmed used voices
    used_voices = set(SELECTED_VOICES.values())
    
    # 4. Filter for unused candidates
    unused = [c for c in candidates if c not in used_voices]
    
    if unused:
        # Pick deterministically from unused
        h = int(hashlib.sha256(key.encode('utf-8')).hexdigest(), 16)
        chosen = unused[h % len(unused)]
        debug_log(f"Assigned NEW unique voice '{chosen}' for '{key}' ({gender}, {language})")
    else:
        # Pool exhausted. Reuse deterministically.
        if candidates:
            h = int(hashlib.sha256(key.encode('utf-8')).hexdigest(), 16)
            chosen = candidates[h % len(candidates)]
            debug_log(f"WARNING: Pool exhausted. Reusing voice '{chosen}' for '{key}' ({gender})")
        else:
             # Extreme fallback
             chosen = 'Joanna' if normalized_gender == 'female' else 'Matthew'
    
    SELECTED_VOICES[key] = chosen
    _save_selected_voices()
    return chosen

def manual_assign_voice(character_name: str, voice_name: str):
    """Manually force an assignment."""
    if voice_name not in POLLY_VOICES_METADATA:
         # Warn but allow if it's a valid AWS voice not in our metadata list
         debug_log(f"Warning: Manually assigned voice '{voice_name}' is not in local metadata.")
    SELECTED_VOICES[character_name.strip()] = voice_name
    _save_selected_voices()


# --- Generation Logic ---

def _make_cache_filename(voice_name: str, text: str) -> str:
    h = hashlib.sha256()
    h.update((voice_name + '||' + text).encode('utf-8'))
    return h.hexdigest() + '.mp3'

def get_cached_tts_path(voice_name: str, text: str, cache_dir: str = None) -> Optional[str]:
    cache_dir = cache_dir or DEFAULT_CACHE_DIR
    fname = _make_cache_filename(voice_name, text)
    path = os.path.join(cache_dir, fname)
    return path if os.path.exists(path) else None

def get_or_generate_tts(text: str, voice_name: str = None, character_name: str = None, 
                       gender: str = 'female', language: str = 'English', cache_dir: str = None) -> str:
    """
    Main entry point for AWS Polly TTS.
    """
    cache_dir = cache_dir or DEFAULT_CACHE_DIR
    
    # Resolve voice
    if not voice_name:
        if character_name:
            voice_name = select_voice_for_character(character_name, gender, language)
        else:
            voice_name = 'Joanna' if gender == 'female' else 'Matthew'
            
    # Check cache
    cached = get_cached_tts_path(voice_name, text, cache_dir)
    if cached:
        return cached

    # Generate
    try:
        import tempfile
        tmp_fd, tmp_path = tempfile.mkstemp(suffix='.mp3')
        os.close(tmp_fd)
        
        generate_polly_audio(text, voice_name, tmp_path)
        
        # Move to cache
        fname = _make_cache_filename(voice_name, text)
        final_path = os.path.join(cache_dir, fname)
        shutil.move(tmp_path, final_path)
        return final_path
    
    except Exception as e:
        debug_log(f"Generation failed: {e}")
        raise

def generate_polly_audio(text: str, voice_name: str, output_path: str):
    """
    Uses AWS Polly to generate speech.
    """
    client = get_polly_client()
    debug_log(f"AWS Polly TTS: voice={voice_name}, text_len={len(text)}")
    
    # Determine engine based on metadata (Neural is preferred if available)
    voice_info = POLLY_VOICES_METADATA.get(voice_name, {})
    engine = voice_info.get('engine', 'neural') # Default to neural
    
    # Some older voices might only be standard, handle fallback if error occurs?
    # For now, assume metadata is correct.
    
    try:
        response = client.synthesize_speech(
            Text=text,
            OutputFormat='mp3',
            VoiceId=voice_name,
            Engine=engine
        )
        
        if "AudioStream" in response:
            with open(output_path, 'wb') as f:
                f.write(response['AudioStream'].read())
        else:
             raise Exception("No AudioStream in Polly response")
        
        # Verify file
        if not os.path.exists(output_path) or os.path.getsize(output_path) < 100:
            raise ValueError("Generated audio file is too small/empty")
            
    except ClientError as e:
        debug_log(f"Polly ClientError: {e}")
        # If Neural engine not supported for this voice/region, retry with standard?
        if 'EngineNotSupported' in str(e) and engine == 'neural':
            debug_log("Neural engine not supported, retrying with standard")
            try:
                response = client.synthesize_speech(
                    Text=text,
                    OutputFormat='mp3',
                    VoiceId=voice_name,
                    Engine='standard'
                )
                if "AudioStream" in response:
                    with open(output_path, 'wb') as f:
                        f.write(response['AudioStream'].read())
                return
            except Exception as e2:
                raise e2
        raise e
    except Exception as e:
        debug_log(f"Polly generation failed: {e}")
        raise
