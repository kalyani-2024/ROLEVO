"""
Q3 Integration Test - Matches API_OVERVIEW.md exactly
Tests ONLY the endpoints documented for Q3.

Flow:
1. Handshake 2: Assessment Launch (Q3 -> Rolevo)
   POST /api/integration/assessment-launch

Q3 implements (not tested here):
- POST /api/receive-cluster-metadata (Handshake 1)
- POST /api/receive-assessment-results (Handshake 3)
"""
import requests
import json
import jwt
import time
import os
from dotenv import load_dotenv

load_dotenv()

# Configuration
BASE_URL = "https://roleplays.trajectorie.com"
Q3_SECRET = os.getenv('Q3_INTEGRATION_SECRET', 'qYx9f4K8mZ2V7cW6e1D0B3TQJvLkH5pA0N6M4RrS8E=')
WEBHOOK_URL = "https://webhook.site/e1d69bf2-6cb7-4856-83a1-e394dce6cc33"

print(f"🎯 Target: {BASE_URL}")
print(f"🔑 Secret (first 8 chars): {Q3_SECRET[:8]}...")
print("=" * 70)


def test_assessment_launch():
    """
    Handshake 2: Assessment Launch
    Q3 -> POST /api/integration/assessment-launch -> Rolevo
    
    This is the MAIN endpoint Q3 uses to launch users into Rolevo.
    """
    print("\n[Handshake 2] Testing Assessment Launch...")
    
    user_id = "EMP_789"
    cluster_id = "6650b144-3dc"  # Use actual cluster ID
    
    # Q3 generates JWT token with user_id and assessment_cluster_id
    payload = {
        "user_id": user_id,
        "assessment_cluster_id": cluster_id,
        "iat": int(time.time()),
        "exp": int(time.time()) + 900  # 15 min expiry
    }
    auth_token = jwt.encode(payload, Q3_SECRET, algorithm="HS256")
    print(f"   Generated JWT: {auth_token[:30]}...")
    
    # Request body per API_OVERVIEW.md
    request_body = {
        "user_id": user_id,
        "user_name": "johndoe",
        "assessment_cluster_id": cluster_id,
        "auth_token": auth_token,
        "return_url": "https://q3.example.com/dashboard",
        "results_url": WEBHOOK_URL  # For testing, send results to webhook
    }
    
    print(f"   Request: POST {BASE_URL}/api/integration/assessment-launch")
    print(f"   Body: {json.dumps(request_body, indent=4)[:200]}...")
    
    response = requests.post(
        f"{BASE_URL}/api/integration/assessment-launch",
        json=request_body,
        headers={"Content-Type": "application/json"},
        timeout=30
    )
    
    print(f"\n   Status: {response.status_code}")
    print(f"   Response: {json.dumps(response.json(), indent=4)}")
    
    if response.status_code == 200 and response.json().get('success'):
        print("\n   ✅ Assessment Launch SUCCESSFUL!")
        print(f"\n   📋 Next Steps for Q3:")
        print(f"      1. Redirect user to: {response.json().get('redirect_url')}")
        print(f"      2. Method: POST with form field assessment_cluster_id={cluster_id}")
        print(f"\n   📋 After user completes roleplay:")
        print(f"      - Rolevo will POST results to: {WEBHOOK_URL}")
        print(f"      - User will be redirected to: return_url")
        return True
    else:
        print(f"\n   ❌ Assessment Launch FAILED")
        print(f"   Error: {response.json().get('detail', response.json().get('error'))}")
        return False


def main():
    print("\n" + "=" * 70)
    print("Q3 INTEGRATION TEST (per API_OVERVIEW.md)")
    print("=" * 70)
    
    success = test_assessment_launch()
    
    print("\n" + "=" * 70)
    if success:
        print("✅ ROLEVO IS READY FOR Q3 INTEGRATION")
    else:
        print("❌ INTEGRATION TEST FAILED")
    print("=" * 70)
    
    print("\n📋 Summary of Rolevo Endpoints (per API_OVERVIEW.md):")
    print("   Q3 calls:")
    print(f"     POST {BASE_URL}/api/integration/assessment-launch")
    print("\n   Rolevo calls (Q3 must implement):")
    print("     POST {Q3_BASE_URL}/api/receive-cluster-metadata")
    print("     POST {Q3_BASE_URL}/api/receive-assessment-results")


if __name__ == "__main__":
    main()
