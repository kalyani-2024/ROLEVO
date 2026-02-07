#!/usr/bin/env python3
"""
Q3 Integration Verification Script with Webhook Testing

This script tests the full Q3 integration flow:
1. POST /api/integration/assessment-launch (simulating Q3 launch)
2. GET /api/integration/assessment-start (simulating user redirect)
3. Verifies callback payloads sent to webhook

Usage:
    python test_q3_webhook_integration.py

Environment:
    Set Q3_INTEGRATION_SECRET in your .env or environment
"""

import os
import sys
import json
import time
import jwt
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Configuration
ROLEVO_BASE_URL = "https://roleplays.trajectorie.com"
WEBHOOK_URL = "https://webhook.site/e1d69bf2-6cb7-4856-83a1-e394dce6cc33"

# Q3 Integration Secret (must match Rolevo's Q3_INTEGRATION_SECRET)
Q3_SECRET = os.environ.get("Q3_INTEGRATION_SECRET", "your-shared-secret-key")

# Test data
TEST_USER_ID = f"TEST-USER-{int(time.time())}"
TEST_USER_NAME = "Test User"
TEST_CLUSTER_ID = "6650b144-3dc"  # Your cluster ID


def print_section(title):
    """Print a section header."""
    print(f"\n{'='*60}")
    print(f" {title}")
    print('='*60)


def generate_q3_jwt(user_id: str, cluster_id: str, expiry_minutes: int = 15) -> str:
    """Generate a JWT token as Q3 would."""
    now = datetime.utcnow()
    payload = {
        "user_id": user_id,
        "assessment_cluster_id": cluster_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=expiry_minutes)).timestamp()),
    }
    token = jwt.encode(payload, Q3_SECRET, algorithm="HS256")
    return token


def test_assessment_launch():
    """Test POST /api/integration/assessment-launch endpoint."""
    print_section("TEST 1: Assessment Launch")
    
    # Generate JWT
    auth_token = generate_q3_jwt(TEST_USER_ID, TEST_CLUSTER_ID)
    print(f"Generated JWT token: {auth_token[:50]}...")
    
    # Build request payload (as Q3 would send)
    payload = {
        "user_id": TEST_USER_ID,
        "user_name": TEST_USER_NAME,
        "assessment_cluster_id": TEST_CLUSTER_ID,
        "auth_token": auth_token,
        "return_url": "https://q3.example.com/dashboard",
        "results_url": WEBHOOK_URL,  # Results will be sent here
    }
    
    print(f"\n📤 Sending POST to {ROLEVO_BASE_URL}/api/integration/assessment-launch")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(
            f"{ROLEVO_BASE_URL}/api/integration/assessment-launch",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        
        print(f"\n📥 Response Status: {response.status_code}")
        
        if response.ok:
            data = response.json()
            print(f"Response Body: {json.dumps(data, indent=2)}")
            
            if data.get("success"):
                redirect_url = data.get("redirect_url")
                print(f"\n✅ SUCCESS! Redirect URL: {redirect_url}")
                return redirect_url
            else:
                print(f"\n❌ API returned success=False: {data.get('detail')}")
                return None
        else:
            print(f"Response Body: {response.text}")
            print(f"\n❌ Request failed with status {response.status_code}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Request error: {e}")
        return None


def test_assessment_start(redirect_url: str):
    """Test GET /api/integration/assessment-start endpoint."""
    print_section("TEST 2: Assessment Start (Follow Redirect)")
    
    if not redirect_url:
        print("❌ No redirect URL to test")
        return False
    
    print(f"📤 Following redirect URL: {redirect_url}")
    
    try:
        # Don't follow redirects automatically so we can see what happens
        response = requests.get(
            redirect_url,
            allow_redirects=False,
            timeout=30,
        )
        
        print(f"\n📥 Response Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code in [302, 301, 303, 307]:
            location = response.headers.get("Location")
            print(f"\n✅ Redirect to: {location}")
            return True
        elif response.status_code == 200:
            print(f"\n⚠️ Got 200 OK (no redirect)")
            print(f"Body preview: {response.text[:500]}...")
            return True
        else:
            print(f"\n❌ Unexpected status code")
            print(f"Body: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Request error: {e}")
        return False


def check_webhook_requests():
    """Check what requests have been received by webhook.site."""
    print_section("TEST 3: Check Webhook Requests")
    
    # Get webhook token ID from URL
    token_id = WEBHOOK_URL.split("/")[-1]
    api_url = f"https://webhook.site/token/{token_id}/requests?sorting=newest"
    
    print(f"📤 Fetching webhook requests from: {api_url}")
    
    try:
        response = requests.get(api_url, timeout=30)
        
        if response.ok:
            data = response.json()
            requests_list = data.get("data", [])
            
            print(f"\n📊 Found {len(requests_list)} requests on webhook")
            
            # Show recent POST requests
            post_requests = [r for r in requests_list if r.get("method") == "POST"]
            print(f"   POST requests: {len(post_requests)}")
            
            for i, req in enumerate(post_requests[:5]):  # Show last 5
                print(f"\n--- Request {i+1} ---")
                print(f"Time: {req.get('created_at')}")
                print(f"URL: {req.get('url')}")
                print(f"Method: {req.get('method')}")
                print(f"User-Agent: {req.get('user_agent')}")
                
                content = req.get("content", "")
                if content:
                    try:
                        parsed = json.loads(content)
                        print(f"Body (JSON):\n{json.dumps(parsed, indent=2)}")
                    except json.JSONDecodeError:
                        print(f"Body (raw): {content[:500]}...")
                        
            return True
        else:
            print(f"\n❌ Failed to fetch webhook requests: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Request error: {e}")
        return False


def send_test_result_to_webhook():
    """Send a test result payload directly to webhook (simulating Rolevo callback)."""
    print_section("TEST 4: Send Test Result to Webhook")
    
    # Build a sample result payload matching results_submission.json schema
    result_payload = {
        "cluster_id": TEST_CLUSTER_ID,
        "cluster_name": "Test Assessment Cluster",
        "cluster_type": "assessment",
        "user_id": TEST_USER_ID,
        "user_name": TEST_USER_NAME,
        "roleplays": [
            {
                "roleplay_id": "RP_TEST001",
                "roleplay_name": "Test Roleplay",
                "stakeholders": "01",
                "max_time": 1800,
                "time_taken": 1200,
                "competencies": [
                    {
                        "competency_code": "COMM_L1",
                        "competency_name": "Communication Level 1",
                        "max_marks": 24,
                        "marks_obtained": 18,
                    },
                    {
                        "competency_code": "EMP_L1",
                        "competency_name": "Empathy Level 1",
                        "max_marks": 21,
                        "marks_obtained": 15,
                    },
                ],
            }
        ],
    }
    
    print(f"📤 Sending test result to: {WEBHOOK_URL}")
    print(f"Payload: {json.dumps(result_payload, indent=2)}")
    
    try:
        response = requests.post(
            WEBHOOK_URL,
            json=result_payload,
            headers={
                "Content-Type": "application/json",
                "X-Rolevo-Source": "test-script",
            },
            timeout=30,
        )
        
        print(f"\n📥 Response Status: {response.status_code}")
        
        if response.ok:
            print(f"✅ Test result sent successfully!")
            print(f"Check webhook.site to see the payload")
            return True
        else:
            print(f"❌ Failed: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Request error: {e}")
        return False


def verify_integration_docs():
    """Verify the integration matches the documented schemas."""
    print_section("INTEGRATION DOCS VERIFICATION")
    
    print("Checking expected Q3 integration flow:")
    print("""
    ┌─────────────────────────────────────────────────────────────┐
    │                    Q3 INTEGRATION FLOW                       │
    ├─────────────────────────────────────────────────────────────┤
    │                                                              │
    │  1. CLUSTER METADATA SYNC (Rolevo → Q3)                     │
    │     POST {Q3_BASE_URL}/api/receive-cluster-metadata          │
    │     When: Admin creates/updates cluster in Rolevo            │
    │                                                              │
    │  2. ASSESSMENT LAUNCH (Q3 → Rolevo)                         │
    │     POST /api/integration/assessment-launch                  │
    │     Payload: user_id, user_name, assessment_cluster_id,      │
    │              auth_token (JWT), return_url, results_url       │
    │     Returns: redirect_url with one-time token                │
    │                                                              │
    │  3. USER REDIRECT (Q3 → Rolevo → Assessment)                │
    │     GET /api/integration/assessment-start?token=...          │
    │     Validates token, creates session, redirects to cluster   │
    │                                                              │
    │  4. RESULTS SUBMISSION (Rolevo → Q3)                        │
    │     POST {results_url} or {Q3_BASE_URL}/api/receive-results │
    │     When: User completes a roleplay                          │
    │                                                              │
    └─────────────────────────────────────────────────────────────┘
    """)
    
    print("Your webhook URL for testing: " + WEBHOOK_URL)
    print(f"Your cluster ID: {TEST_CLUSTER_ID}")
    print(f"Q3 Secret configured: {'Yes' if Q3_SECRET != 'your-shared-secret-key' else 'No (using default)'}")


def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║       Q3 INTEGRATION VERIFICATION WITH WEBHOOK TESTING       ║
╠══════════════════════════════════════════════════════════════╣
║  Rolevo URL: https://roleplays.trajectorie.com               ║
║  Webhook:    https://webhook.site/e1d69bf2-...               ║
║  Cluster:    6650b144-3dc                                     ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    # Verify docs
    verify_integration_docs()
    
    # Check what's already on webhook
    check_webhook_requests()
    
    # Test the assessment launch flow
    redirect_url = test_assessment_launch()
    
    if redirect_url:
        test_assessment_start(redirect_url)
    
    # Send test result
    send_test_result_to_webhook()
    
    print_section("SUMMARY")
    print("""
📋 To test the full flow manually:

1. Go to your hosted Rolevo site
2. Have Q3 call assessment-launch with proper JWT
3. User follows redirect_url 
4. Complete a roleplay
5. Check webhook.site for the results callback

Or use this URL pattern (after getting a fresh token):
https://roleplays.trajectorie.com/api/integration/assessment-start?token=<TOKEN>&cluster_id=6650b144-3dc

The token you provided (UJz43kaHnwSAaqMkotVZqU2SvKWxCxsUxD0sebRgrzA) 
is likely expired - tokens are valid for 10-15 minutes only.
    """)


if __name__ == "__main__":
    main()
