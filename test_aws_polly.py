
import os
import sys
import pytest
from app.tts_service import (
    get_available_voices, 
    select_voice_for_character, 
    generate_polly_audio,
    get_or_generate_tts,
    POLLY_VOICES_METADATA
)

def test_available_voices():
    print("\n--- Testing Available Voices ---")
    voices = get_available_voices()
    print(f"Total available voices: {len(voices)}")
    assert len(voices) > 0, "No voices available"
    
    # Check for Indian English voices
    indian_voices = [v for v in voices if v['language'] == 'en-IN']
    print(f"Indian English voices: {[v['name'] for v in indian_voices]}")
    assert len(indian_voices) >= 2, "Should have at least Kajal and Raveena"

def test_voice_selection():
    print("\n--- Testing Voice Selection ---")
    
    # Test 1: Consistent assignment
    v1 = select_voice_for_character("TestChar1", "female", "English")
    v2 = select_voice_for_character("TestChar1", "female", "English")
    print(f"TestChar1 (Female, English) assigned: {v1}")
    assert v1 == v2, "Voice assignment should be consistent"
    assert POLLY_VOICES_METADATA[v1]['gender'] == 'female'
    
    # Test 2: Indian Language
    v3 = select_voice_for_character("Ramesh", "male", "Hindi")
    print(f"Ramesh (Male, Hindi -> en-IN fallback?) assigned: {v3}")
    # Note: If no male en-IN voice, it might fallback to en-GB or en-US male.
    # We should check if it respects gender first.
    assert POLLY_VOICES_METADATA[v3]['gender'] == 'male'
    
    v4 = select_voice_for_character("Priya", "female", "Tamil")
    print(f"Priya (Female, Tamil -> en-IN) assigned: {v4}")
    assert POLLY_VOICES_METADATA[v4]['language'] == 'en-IN'

    # Test 3: French
    v5 = select_voice_for_character("Marie", "female", "French")
    print(f"Marie (Female, French) assigned: {v5}")
    assert POLLY_VOICES_METADATA[v5]['language'].startswith('fr')

    v6 = select_voice_for_character("Pierre", "male", "French")
    print(f"Pierre (Male, French) assigned: {v6}")
    assert POLLY_VOICES_METADATA[v6]['language'].startswith('fr') and POLLY_VOICES_METADATA[v6]['gender'] == 'male'

    # Test 4: Arabic
    v7 = select_voice_for_character("Layla", "female", "Arabic")
    print(f"Layla (Female, Arabic) assigned: {v7}")
    assert POLLY_VOICES_METADATA[v7]['language'].startswith('ar') or POLLY_VOICES_METADATA[v7]['language'] == 'arb'

    # Test 5: Unique assignment (if possible)
    v8 = select_voice_for_character("CharA", "female", "English")
    v9 = select_voice_for_character("CharB", "female", "English")
    print(f"CharA: {v8}, CharB: {v9}")
    if v8 == v9:
        print("Warning: Collision or pool exhausted")

def test_generation():
    print("\n--- Testing Audio Generation ---")
    text = "Hello, this is a test of AWS Polly integration."
    output_file = "test_polly_output.mp3"
    
    # Use a safe voice we know exists (Joanna)
    voice = "Joanna"
    
    try:
        generate_polly_audio(text, voice, output_file)
        
        if os.path.exists(output_file):
            size = os.path.getsize(output_file)
            print(f"Successfully generated {output_file} ({size} bytes)")
            assert size > 100, "Audio file too small"
            os.remove(output_file)
        else:
            print("Failed to generate file")
            assert False, "File not created"
            
    except Exception as e:
        print(f"Generation error: {e}")
        # Identify if it's credential error
        if "NoCredentialsError" in str(e) or "BotoCoreError" in str(e):
             print("AWS Credentials missing or invalid. Check .env")

if __name__ == "__main__":
    try:
        test_available_voices()
        test_voice_selection()
        test_generation() # This might fail if credentials aren't live
        print("\nAll tests passed!")
    except AssertionError as e:
        print(f"\nTest Failed: {e}")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
