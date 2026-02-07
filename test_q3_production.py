"""
Test script for Q3 Trajectorie-style Integration Flow on PRODUCTION/HOSTED Environment.
Tests:
1. /api/integration/assessment-launch (SSO)

Target: https://roleplays.trajectorie.com
"""
import requests
import json
import jwt
import time
import os

# Configuration
BASE_URL = "https://roleplays.trajectorie.com"

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

Q3_SHARED_SECRET = os.getenv('Q3_INTEGRATION_SECRET', "your-shared-secret-key")
print(f"Loaded Q3_SHARED_SECRET: {Q3_SHARED_SECRET[:3]}***{Q3_SHARED_SECRET[-3:] if len(Q3_SHARED_SECRET)>3 else ''} (from env: {bool(os.getenv('Q3_INTEGRATION_SECRET'))})")

def generate_q3_token(user_id, cluster_id):
    """Generate JWT token as Q3 would"""
    # Use UTC time to avoid timezone issues
    now = int(time.time())
    payload = {
        "user_id": user_id,
        "assessment_cluster_id": cluster_id,
        "iat": now,
        "exp": now + 900  # 15 min expiry
    }
    return jwt.encode(payload, Q3_SHARED_SECRET, algorithm="HS256")

def test_assessment_launch():
    """Test the launch endpoint"""
    print(f"\n=== Testing Assessment Launch (SSO) on {BASE_URL} ===")
    
    user_id = "Q3-PROD-TEST-001"
    cluster_id = "6650b144-3dc" # Use the cluster ID that exists on prod
    
    # Generate token
    token = generate_q3_token(user_id, cluster_id)
    print(f"Generated JWT: {token[:20]}...")
    
    payload = {
        "user_id": user_id,
        "user_name": "Prod Test User",
        "assessment_cluster_id": cluster_id,
        "auth_token": token,
        "return_url": "https://webhook.site/e1d69bf2-6cb7-4856-83a1-e394dce6cc33", # Redirect back here
        "results_url": "https://webhook.site/e1d69bf2-6cb7-4856-83a1-e394dce6cc33"  # Post results here
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/integration/assessment-launch",
            json=payload,
            timeout=30
        )
        
        print(f"Status: {response.status_code}")
        print("Response:", json.dumps(response.json(), indent=2))
        
        if response.status_code == 200 and response.json().get('success'):
            print("\n✅ Launch successful!")
            redirect_url = response.json().get('redirect_url')
            if redirect_url:
                print(f"👉 Redirect User To: {redirect_url}")
                print(f"   (POST param assessment_cluster_id={cluster_id})")
        else:
            print("❌ Launch failed")
            print(f"Headers: {response.headers}")
            print(f"Content: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_assessment_launch()
