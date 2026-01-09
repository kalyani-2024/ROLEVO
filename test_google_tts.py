"""
Test Google Cloud TTS Setup

Run this script to verify Google Cloud TTS is working correctly.

Before running:
1. Download your service account JSON key from Google Cloud Console
2. Set the environment variable:
   $env:GOOGLE_APPLICATION_CREDENTIALS = "C:\path\to\your-service-account.json"
   
Or place the JSON file path in your .env file.
"""

import os
import sys

def test_google_tts():
    print("Testing Google Cloud TTS...")
    
    # Check if credentials are set
    creds = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', '')
    if not creds:
        print("\n❌ GOOGLE_APPLICATION_CREDENTIALS not set!")
        print("\nTo set up Google Cloud TTS:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create a project or select existing")
        print("3. Enable 'Cloud Text-to-Speech API'")
        print("4. Go to 'IAM & Admin' → 'Service Accounts'")
        print("5. Create a service account and download JSON key")
        print("6. Run in PowerShell:")
        print('   $env:GOOGLE_APPLICATION_CREDENTIALS = "C:\\path\\to\\your-key.json"')
        return False
    
    if not os.path.exists(creds):
        print(f"\n❌ Credentials file not found: {creds}")
        return False
    
    print(f"✅ Credentials file found: {creds}")
    
    try:
        from google.cloud import texttospeech
        print("✅ google-cloud-texttospeech package installed")
        
        # Try to create a client
        client = texttospeech.TextToSpeechClient()
        print("✅ Successfully created TTS client")
        
        # Test synthesis
        synthesis_input = texttospeech.SynthesisInput(text="Hello, this is a test of Google Cloud Text to Speech.")
        
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name="en-US-Neural2-D"  # Male voice
        )
        
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )
        
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
        
        # Save test file
        test_file = "test_google_tts_output.mp3"
        with open(test_file, 'wb') as out:
            out.write(response.audio_content)
        
        if os.path.exists(test_file) and os.path.getsize(test_file) > 0:
            print(f"✅ Audio generated successfully: {test_file} ({os.path.getsize(test_file)} bytes)")
            print("\n🎉 Google Cloud TTS is working correctly!")
            return True
        else:
            print("❌ Failed to generate audio file")
            return False
            
    except ImportError:
        print("❌ google-cloud-texttospeech not installed. Run:")
        print("   pip install google-cloud-texttospeech")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_google_tts()
