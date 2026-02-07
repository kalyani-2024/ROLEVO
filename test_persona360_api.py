"""
Test script to call Persona360 API directly and see what response format we get.
This will help debug why only some traits are showing in the report.
"""
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

# API Configuration
API_URL = os.getenv('PERSONA360_API_URL', 'http://api.persona360.rapeti.dev:8290/predict')
API_KEY = os.getenv('PERSONA360_API_KEY', '')

def test_api_with_audio(audio_file_path, age=30, gender="Male"):
    """Test the Persona360 API with an audio file"""
    
    if not os.path.exists(audio_file_path):
        print(f"ERROR: Audio file not found: {audio_file_path}")
        return
    
    print(f"=" * 60)
    print(f"Testing Persona360 API")
    print(f"=" * 60)
    print(f"API URL: {API_URL}")
    print(f"Audio file: {audio_file_path}")
    print(f"File size: {os.path.getsize(audio_file_path)} bytes")
    print(f"Parameters: age={age}, gender={gender}")
    print(f"=" * 60)
    
    headers = {"accept": "application/json"}
    if API_KEY:
        headers["x-api-key"] = API_KEY
    
    data = {
        "mode": "audio",
        "age": str(age),
        "gender": gender
    }
    
    try:
        print("\nSending request to API...")
        with open(audio_file_path, "rb") as audio_file:
            files = {"file": (os.path.basename(audio_file_path), audio_file)}
            response = requests.post(
                API_URL,
                headers=headers,
                files=files,
                data=data,
                timeout=120
            )
        
        print(f"\nResponse Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            
            print(f"\n{'=' * 60}")
            print("SUCCESS! API Response:")
            print(f"{'=' * 60}")
            
            # Print full response
            print(f"\nFULL RAW RESPONSE:\n{json.dumps(result, indent=2)}")
            
            # Analyze the response structure
            print(f"\n{'=' * 60}")
            print("RESPONSE ANALYSIS:")
            print(f"{'=' * 60}")
            
            if isinstance(result, dict):
                print(f"\nTop-level keys: {list(result.keys())}")
                
                for key, value in result.items():
                    print(f"\n  Key: '{key}'")
                    print(f"    Type: {type(value).__name__}")
                    if isinstance(value, dict):
                        print(f"    Nested keys: {list(value.keys())}")
                        print(f"    Sample values: {dict(list(value.items())[:5])}")
                    elif isinstance(value, list):
                        print(f"    List length: {len(value)}")
                        if len(value) > 0:
                            print(f"    First item type: {type(value[0]).__name__}")
                            print(f"    First item: {value[0]}")
                    elif isinstance(value, (int, float)):
                        print(f"    Value: {value}")
                    elif isinstance(value, str):
                        print(f"    Value: '{value[:100]}...' " if len(str(value)) > 100 else f"    Value: '{value}'")
            else:
                print(f"Response is not a dict, it's: {type(result)}")
                print(f"Content: {result}")
                
        else:
            print(f"\nERROR Response:")
            print(f"Status: {response.status_code}")
            print(f"Body: {response.text}")
            
    except requests.exceptions.Timeout:
        print("\nERROR: Request timed out (120 seconds)")
    except requests.exceptions.RequestException as e:
        print(f"\nERROR: Request failed: {str(e)}")
    except json.JSONDecodeError as e:
        print(f"\nERROR: Failed to parse JSON response: {str(e)}")
        print(f"Raw response text: {response.text[:500]}")
    except Exception as e:
        print(f"\nERROR: Unexpected error: {str(e)}")


def find_audio_files():
    """Find audio files in the uploads folder"""
    audio_extensions = ['.mp3', '.wav', '.webm', '.ogg', '.m4a', '.mp4', '.avi', '.mov']
    uploads_dir = os.path.join(os.path.dirname(__file__), 'uploads')
    app_uploads_dir = os.path.join(os.path.dirname(__file__), 'app', 'uploads')
    
    audio_files = []
    
    for search_dir in [uploads_dir, app_uploads_dir, '.']:
        if os.path.exists(search_dir):
            for root, dirs, files in os.walk(search_dir):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in audio_extensions):
                        audio_files.append(os.path.join(root, file))
    
    return audio_files


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Audio file path provided as argument
        audio_path = sys.argv[1]
        age = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        gender = sys.argv[3] if len(sys.argv) > 3 else "Male"
        test_api_with_audio(audio_path, age, gender)
    else:
        # Try to find audio files
        print("No audio file specified. Searching for audio files...")
        audio_files = find_audio_files()
        
        if audio_files:
            print(f"\nFound {len(audio_files)} audio file(s):")
            for i, f in enumerate(audio_files[:10]):  # Show first 10
                print(f"  {i+1}. {f}")
            
            print(f"\nTo test, run:")
            print(f'  python test_persona360_api.py "{audio_files[0]}" 30 Male')
        else:
            print("\nNo audio files found in uploads folder.")
            print("\nUsage:")
            print("  python test_persona360_api.py <audio_file_path> [age] [gender]")
            print("\nExample:")
            print('  python test_persona360_api.py "C:\\path\\to\\audio.mp3" 30 Male')
