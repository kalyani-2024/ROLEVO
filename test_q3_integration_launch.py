"""
Test script for Q3 Trajectorie-style Integration Flow.
Tests:
1. /api/integration/assessment-launch (SSO)
2. result callback (simulation)
"""
import requests
import json
import jwt
import time
import os
from datetime import datetime, timedelta

# Configuration
BASE_URL = "http://127.0.0.1:5000"
Q3_SHARED_SECRET = "your-shared-secret-key" # Default placeholder, will read from env if available

# Try to read real secret from .env manually if running locally
try:
    with open('.env', 'r') as f:
        for line in f:
            if line.startswith('Q3_INTEGRATION_SECRET='):
                val = line.split('=', 1)[1].strip().strip('"').strip("'")
                if val:
                    Q3_SHARED_SECRET = val
                    print(f"Loaded Q3_SHARED_SECRET from .env")
                break
except:
    pass

def generate_q3_token(user_id, cluster_id):
    """Generate JWT token as Q3 would"""
    payload = {
        "user_id": user_id,
        "assessment_cluster_id": cluster_id,
        "iat": int(time.time()),
        "exp": int(time.time()) + 900  # 15 min expiry
    }
    return jwt.encode(payload, Q3_SHARED_SECRET, algorithm="HS256")

def test_assessment_launch():
    """Test the launch endpoint"""
    print("\n=== Testing Assessment Launch (SSO) ===")
    
    user_id = "Q3-USER-TEST-002"
    cluster_id = "b4bf406c-4f9" # Replace with valid cluster ID from your DB if needed
    
    # Generate token
    token = generate_q3_token(user_id, cluster_id)
    print(f"Generated JWT: {token[:20]}...")
    
    payload = {
        "user_id": user_id,
        "user_name": "Test Q3 User",
        "assessment_cluster_id": cluster_id,
        "auth_token": token,
        "return_url": "https://q3-dev.example.com/dashboard",
        "results_url": "https://webhook.site/e1d69bf2-6cb7-4856-83a1-e394dce6cc33"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/integration/assessment-launch",
            json=payload
        )
        
        print(f"Status: {response.status_code}")
        print("Response:", json.dumps(response.json(), indent=2))
        
        if response.status_code == 200 and response.json().get('success'):
            print("✅ Launch successful!")
            return response.json()
        else:
            print("❌ Launch failed")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

if __name__ == "__main__":
    test_assessment_launch()
