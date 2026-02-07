
import os
import boto3
from dotenv import load_dotenv

# Load .env file
load_dotenv()

try:
    # Initialize Polly client
    region = os.getenv('AWS_REGION', 'us-east-1')
    client = boto3.client('polly', region_name=region)
    
    # Describe voices
    response = client.describe_voices()
    
    voices = response.get('Voices', [])
    print(f"Found {len(voices)} voices total.")
    
    target_langs = ['fr-FR', 'fr-CA', 'ar-AE', 'ar-SA', 'ar-QA', 'ar-KW'] # common arabic locales? Polly usually uses ar-AE or just ar.
    # Actually Polly uses 'arb' for Arabic (Standard)? Or 'ar-AE'? Let's check 'ar' prefix.
    
    print("\n--- French Voices ---")
    fr_count = 0
    for v in voices:
        if v['LanguageCode'].startswith('fr-'):
            print(f"{v['Name']} ({v['Gender']}, {v['LanguageCode']}) - {v['SupportedEngines']}")
            fr_count += 1
    print(f"Total French found: {fr_count}")

    print("\n--- Arabic Voices ---")
    ar_count = 0
    for v in voices:
         if v['LanguageCode'].startswith('ar'):
            print(f"{v['Name']} ({v['Gender']}, {v['LanguageCode']}) - {v['SupportedEngines']}")
            ar_count += 1
    print(f"Total Arabic found: {ar_count}")

except Exception as e:
    print(f"Error: {e}")
