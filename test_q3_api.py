"""
Q3 Integration API Test Script with JWT Authentication
Tests all endpoints for Q3/AIO integration

JWT Authentication Flow:
========================
1. POST /api/auth/token - Get JWT token using client credentials
2. Use JWT in Authorization header: "Bearer <token>"

API Endpoints:
=============
- POST /api/auth/token - Get JWT access token
- POST /api/auth/init - Initialize SSO session
- GET /api/auth/start - User lands here (redirects to roleplay)
- GET /api/rolevo/clusters - List all available clusters
- GET /api/rolevo/scores/user/<user_id> - Scores by user
- GET /api/rolevo/scores/cluster/<cluster_id> - Scores by cluster
- GET /api/rolevo/scores/play/<play_id> - Scores by play
"""

import requests
import json

BASE_URL = "http://127.0.0.1:5000"  # Change to production URL

# Client credentials (set in .env as AIO_CLIENT_SECRET or AIO_API_TOKEN)
CLIENT_ID = "q3_platform"
CLIENT_SECRET = "test_local_token_123"


def get_jwt_token():
    """Get JWT access token"""
    print("\n=== Getting JWT Token ===")
    response = requests.post(f"{BASE_URL}/api/auth/token", json={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    })
    print(f"Status: {response.status_code}")
    data = response.json()
    
    if data.get('success'):
        print(f"Token Type: {data['token_type']}")
        print(f"Expires In: {data['expires_in']} seconds")
        print(f"Token: {data['access_token'][:50]}...")
        return data['access_token']
    else:
        print(f"Error: {data.get('error')}")
        return None


def test_clusters(jwt_token):
    """Test fetching clusters"""
    print("\n=== Testing Clusters List ===")
    response = requests.get(
        f"{BASE_URL}/api/rolevo/clusters",
        headers={"Authorization": f"Bearer {jwt_token}"}
    )
    print(f"Status: {response.status_code}")
    data = response.json()
    if data.get('success'):
        print(f"Found {len(data.get('clusters', []))} clusters")
        for c in data.get('clusters', [])[:3]:
            print(f"  - {c['cluster_id']}: {c['cluster_name']}")
    return data


def test_sso_init(jwt_token):
    """Test SSO initialization"""
    print("\n=== Testing SSO Init ===")
    response = requests.post(
        f"{BASE_URL}/api/auth/init",
        json={
            "api_token": CLIENT_SECRET,  # Still uses api_token for SSO
            "user_id": "TEST-USER-001",
            "user_name": "Test User",
            "cluster_id": "b4bf406c-4f9",
            "callback_url": "https://webhook.site/e1d69bf2-6cb7-4856-83a1-e394dce6cc33"
        }
    )
    print(f"Status: {response.status_code}")
    data = response.json()
    print(json.dumps(data, indent=2))
    return data


def test_scores_by_user(jwt_token, user_id):
    """Test fetching scores by user with JWT"""
    print(f"\n=== Testing Scores by User: {user_id} ===")
    response = requests.get(
        f"{BASE_URL}/api/rolevo/scores/user/{user_id}",
        headers={"Authorization": f"Bearer {jwt_token}"}
    )
    print(f"Status: {response.status_code}")
    data = response.json()
    if data.get('success'):
        print(f"Total Roleplays: {data.get('total_roleplays', 0)}")
        for rp in data.get('roleplays', [])[:2]:
            print(f"  - {rp['roleplay_name']}: Score {rp['overall_score']}")
    return data


def test_scores_by_cluster(jwt_token, cluster_id):
    """Test fetching scores by cluster with JWT"""
    print(f"\n=== Testing Scores by Cluster: {cluster_id} ===")
    response = requests.get(
        f"{BASE_URL}/api/rolevo/scores/cluster/{cluster_id}",
        headers={"Authorization": f"Bearer {jwt_token}"}
    )
    print(f"Status: {response.status_code}")
    data = response.json()
    if data.get('success'):
        print(f"Total Users: {data.get('total_users', 0)}")
    return data


if __name__ == "__main__":
    print("=" * 60)
    print("Q3 Integration API Tests - JWT Authentication")
    print(f"Target: {BASE_URL}")
    print("=" * 60)
    
    # Get JWT token first
    jwt_token = get_jwt_token()
    
    if jwt_token:
        # Test all endpoints
        test_clusters(jwt_token)
        test_sso_init(jwt_token)
        test_scores_by_user(jwt_token, "EMP-12345")
        test_scores_by_cluster(jwt_token, "b4bf406c-4f9")
        
        print("\n" + "=" * 60)
        print("All tests completed!")
        print("=" * 60)
    else:
        print("\n❌ Failed to get JWT token. Check credentials.")
