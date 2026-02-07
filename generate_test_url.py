#!/usr/bin/env python3
"""
Generate assessment launch URL for testing Q3 integration with webhook.
This will call the production Rolevo server and get a redirect URL.
"""

import os
import time
import jwt
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# Configuration
ROLEVO_BASE_URL = "https://roleplays.trajectorie.com"
WEBHOOK_URL = "https://webhook.site/e1d69bf2-6cb7-4856-83a1-e394dce6cc33"
Q3_SECRET = os.environ.get("Q3_INTEGRATION_SECRET")
TEST_CLUSTER_ID = "6650b144-3dc"  # Your cluster ID

print("=" * 60)
print("GENERATE ASSESSMENT URL FOR TESTING")
print("=" * 60)

if not Q3_SECRET:
    print("ERROR: Q3_INTEGRATION_SECRET not found in .env")
    exit(1)

print(f"Secret: {Q3_SECRET[:8]}...{Q3_SECRET[-4:]}")
print(f"Cluster: {TEST_CLUSTER_ID}")
print(f"Webhook: {WEBHOOK_URL}")

# Generate unique test user
test_user = f"TEST-{int(time.time())}"
print(f"Test User: {test_user}")

# Generate JWT token
now = datetime.utcnow()
jwt_payload = {
    "user_id": test_user,
    "assessment_cluster_id": TEST_CLUSTER_ID,
    "iat": int(now.timestamp()),
    "exp": int((now + timedelta(minutes=15)).timestamp()),
}
auth_token = jwt.encode(jwt_payload, Q3_SECRET, algorithm="HS256")

# Build launch request
launch_payload = {
    "user_id": test_user,
    "user_name": "Test User",
    "assessment_cluster_id": TEST_CLUSTER_ID,
    "auth_token": auth_token,
    "return_url": "https://q3.example.com/dashboard",
    "results_url": WEBHOOK_URL,
}

print("\n" + "-" * 40)
print("Calling assessment-launch...")
print("-" * 40)

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
        if data.get("success"):
            redirect_url = data.get("redirect_url")
            print("\n" + "=" * 60)
            print("SUCCESS! Open this URL in your browser:")
            print("=" * 60)
            print(f"\n{redirect_url}\n")
            print("=" * 60)
            print("\nAfter completing the roleplay, check webhook.site:")
            print("https://webhook.site/#!/e1d69bf2-6cb7-4856-83a1-e394dce6cc33")
            print("\nThe results JSON will be POSTed there automatically.")
        else:
            print(f"Error: {data.get('detail')}")
    else:
        print(f"Error: {resp.text}")

except Exception as e:
    print(f"Error: {e}")
