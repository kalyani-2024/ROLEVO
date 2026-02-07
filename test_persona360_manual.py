
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to path so we can import app modules
sys.path.append(os.getcwd())

from app.persona360_service import analyze_audio_for_16pf

def test_analysis():
    file_path = r"app\static\merged_audio\merged_play354_20260121_003925.mp3"
    
    # Check if file exists
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    print(f"Analyzing file: {file_path}")
    print("-" * 50)
    
    # Call the service
    success, result = analyze_audio_for_16pf(file_path)
    
    print("-" * 50)
    print(f"Analysis Success: {success}")
    if success:
        print("Result Data:")
        import json
        print(json.dumps(result, indent=2))
    else:
        print(f"Error: {result}")

if __name__ == "__main__":
    test_analysis()
