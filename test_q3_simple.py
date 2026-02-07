#!/usr/bin/env python3
"""
Simple Q3 Integration Test with proper JWT authentication
"""

import os
import json
import time
import jwt
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Configuration
ROLEVO_BASE_URL = "https://roleplays.trajectorie.com"
WEBHOOK_URL = "https://webhook.site/e1d69bf2-6cb7-4856-83a1-e394dce6cc33"
Q3_SECRET = os.environ.get("Q3_INTEGRATION_SECRET", "")
TEST_CLUSTER_ID = "6650b144-3dc"

print("=" * 60)
print("Q3 INTEGRATION TEST")
print("=" * 60)
print(f"Secret loaded: {'Yes (' + Q3_SECRET[:5] + '...)' if Q3_SECRET else 'No'}")
print(f"Webhook: {WEBHOOK_URL}")
print(f"Cluster: {TEST_CLUSTER_ID}")
print()

if not Q3_SECRET:
    print("ERROR: Q3_INTEGRATION_SECRET not found in environment")
    exit(1)

# Generate test user ID
test_user = f"TEST-{int(time.time())}"

# Generate JWT
now = datetime.utcnow()
payload = {
    "user_id": test_user,
    "assessment_cluster_id": TEST_CLUSTER_ID,
    "iat": int(now.timestamp()),
    "exp": int((now + timedelta(minutes=15)).timestamp()),
}
auth_token = jwt.encode(payload, Q3_SECRET, algorithm="HS256")
print(f"Generated JWT for user: {test_user}")

# Build assessment launch request
launch_payload = {
    "user_id": test_user,
    "user_name": "Test User",
    "assessment_cluster_id": TEST_CLUSTER_ID,
    "auth_token": auth_token,
    "return_url": "https://q3.example.com/dashboard",
    "results_url": WEBHOOK_URL,
}

print("\n" + "-" * 40)
print("TEST 1: Assessment Launch")
print("-" * 40)
print(f"POST {ROLEVO_BASE_URL}/api/integration/assessment-launch")

try:
    resp = requests.post(
        f"{ROLEVO_BASE_URL}/api/integration/assessment-launch",
        json=launch_payload,
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
    print(f"Status: {resp.status_code}")
    
    if resp.ok:
        data = resp.json()
        print(f"Success: {data.get('success')}")
        if data.get('success'):
            redirect_url = data.get('redirect_url')
            print(f"Redirect URL: {redirect_url}")
            
            print("\n" + "-" * 40)
            print("TEST 2: Follow Redirect (assessment-start)")
            print("-" * 40)
            
            # Follow the redirect
            resp2 = requests.get(redirect_url, allow_redirects=False, timeout=30)
            print(f"Status: {resp2.status_code}")
            
            if resp2.status_code in [301, 302, 303, 307]:
                print(f"Redirects to: {resp2.headers.get('Location')}")
                print("SUCCESS! User would be logged in and redirected to cluster")
            else:
                print(f"Body: {resp2.text[:200]}")
        else:
            print(f"Error: {data.get('detail')}")
    else:
        print(f"Error: {resp.text}")

except Exception as e:
    print(f"Error: {e}")

print("\n" + "-" * 40)
print("TEST 3: Send Test Result to Webhook")
print("-" * 40)

test_result = {
    "cluster_id": TEST_CLUSTER_ID,
    "cluster_name": "Test Cluster",
    "cluster_type": "assessment",
    "user_id": test_user,
    "user_name": "Test User",
    "roleplays": [{
        "roleplay_id": "RP_TEST",
        "roleplay_name": "Test RP",
        "stakeholders": "01",
        "max_time": 1800,
        "time_taken": 1200,
        "competencies": [{
            "competency_code": "COMM_L1",
            "competency_name": "Communication Level 1",
            "max_marks": 24,
            "marks_obtained": 18,
        }]
    }]
}

try:
    resp = requests.post(WEBHOOK_URL, json=test_result, timeout=30)
    print(f"Status: {resp.status_code}")
    if resp.ok:
        print("Result payload sent to webhook.site successfully")
        print("Check: https://webhook.site/#!/e1d69bf2-6cb7-4856-83a1-e394dce6cc33")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print("""
To test the full flow:
1. The URL you provided was EXPIRED (tokens last ~10-15 min)
2. Use the redirect_url above to access the assessment
3. Complete a roleplay
4. Check webhook.site for the results callback

Your token: UJz43kaHnwSAaqMkotVZqU2SvKWxCxsUxD0sebRgrzA
This token is expired. Get a fresh one by calling assessment-launch.
""")
