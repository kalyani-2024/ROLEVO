
import os
import sys
import hashlib
import json
import shutil
import boto3

# Mock the parts of the app we need
POLLY_VOICES_METADATA = {
    'Joanna': {'gender': 'female', 'language': 'en-US', 'engine': 'neural'},
    'Matthew': {'gender': 'male', 'language': 'en-US', 'engine': 'neural'},
    'Kajal': {'gender': 'female', 'language': 'en-IN', 'engine': 'neural'},
    'Aditi': {'gender': 'female', 'language': 'en-IN', 'engine': 'standard'},
}

def minimal_polly_test():
    print("--- Minimal Polly Connection Test ---")
    try:
        # Load env vars manually if dotenv not available/working
        # (Assuming they are already in the shell env or .env file)
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            print("dotenv not installed, relying on system env vars")

        region = os.getenv('AWS_REGION', 'us-east-1')
        print(f"Region: {region}")
        
        client = boto3.client('polly', region_name=region)
        print("Boto3 client created.")
        
        # 1. Test Describe Voices (Connectivity Check)
        print("Fetching usable voices...")
        response = client.describe_voices()
        voices = response.get('Voices', [])
        print(f"Successfully connected! Found {len(voices)} voices available.")
        
        # 2. Test Synthesis
        print("Testing synthesis (text='Hello World', voice='Joanna')...")
        response = client.synthesize_speech(
            Text="Hello World",
            OutputFormat='mp3',
            VoiceId='Joanna',
            Engine='neural'
        )
        
        if "AudioStream" in response:
            with open('minimal_test_output.mp3', 'wb') as f:
                f.write(response['AudioStream'].read())
            print("Success! Audio file 'minimal_test_output.mp3' created.")
            print(f"File size: {os.path.getsize('minimal_test_output.mp3')} bytes")
        else:
            print("Failed: No AudioStream in response")

    except Exception as e:
        print(f"\nFAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    minimal_polly_test()
