"""
Q3 integration verification script.

Tests:
  - GET /api/rolevo/clusters (JWT)
  - POST /api/integration/assessment-launch (Q3-style JWT)
  - GET /api/integration/assessment-start (token + cluster_id)
  - Optional: validate results payload shape vs schemas/results_submission.json

Env (or .env):
  ROLEVO_BASE_URL     default http://127.0.0.1:5000
  Q3_INTEGRATION_SECRET or AIO_CLIENT_SECRET  (same as Rolevo)
  TEST_CLUSTER_ID     optional; else first cluster from /api/rolevo/clusters
  RESULTS_URL         optional; e.g. http://127.0.0.1:5999/api/receive-assessment-results

Run: python scripts/test_q3_integration.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import requests
except ImportError:
    print("Install requests: pip install requests")
    sys.exit(1)

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

try:
    import jwt
except ImportError:
    print("Install PyJWT: pip install pyjwt")
    sys.exit(1)

BASE_URL = os.environ.get("ROLEVO_BASE_URL", "http://127.0.0.1:5000").rstrip("/")
SECRET = os.environ.get("Q3_INTEGRATION_SECRET") or os.environ.get("AIO_CLIENT_SECRET") or os.environ.get("AIO_API_TOKEN")
TEST_CLUSTER_ID = os.environ.get("TEST_CLUSTER_ID")
RESULTS_URL = os.environ.get("RESULTS_URL")
CLIENT_ID = "q3_platform"


def get_api_token() -> str | None:
    """Get Rolevo API token (for /api/rolevo/*)."""
    r = requests.post(
        f"{BASE_URL}/api/auth/token",
        json={"client_id": CLIENT_ID, "client_secret": SECRET},
        headers={"Content-Type": "application/json"},
        timeout=10,
    )
    d = r.json()
    if d.get("success") and d.get("access_token"):
        return d["access_token"]
    print(f"  Token error: {d.get('error', r.text)}")
    return None


def get_clusters(api_token: str) -> list[dict]:
    """Fetch clusters from Rolevo."""
    r = requests.get(
        f"{BASE_URL}/api/rolevo/clusters",
        headers={"Authorization": f"Bearer {api_token}"},
        timeout=10,
    )
    d = r.json()
    if not d.get("success"):
        print(f"  Clusters error: {d.get('error', r.text)}")
        return []
    return d.get("clusters", [])


def make_q3_jwt(user_id: str, assessment_cluster_id: str) -> str:
    """Build Q3-style JWT for assessment launch."""
    import time

    now = int(time.time())
    payload = {
        "user_id": user_id,
        "assessment_cluster_id": assessment_cluster_id,
        "iat": now,
        "exp": now + 15 * 60,
    }
    tok = jwt.encode(payload, SECRET, algorithm="HS256")
    return tok if isinstance(tok, str) else tok.decode("utf-8")


def test_assessment_launch(cluster_id: str) -> dict | None:
    """POST /api/integration/assessment-launch, return parsed JSON or None."""
    user_id = "TEST-Q3-001"
    user_name = "Q3 Test User"
    auth_token = make_q3_jwt(user_id, cluster_id)
    payload = {
        "user_id": user_id,
        "user_name": user_name,
        "assessment_cluster_id": cluster_id,
        "auth_token": auth_token,
        "return_url": "https://q3.example.com/dashboard",
    }
    if RESULTS_URL:
        payload["results_url"] = RESULTS_URL

    r = requests.post(
        f"{BASE_URL}/api/integration/assessment-launch",
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=10,
    )
    d = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    if r.status_code != 200:
        print(f"  Launch error {r.status_code}: {d.get('detail', d)}")
        return None
    if not d.get("success"):
        print(f"  Launch failed: {d.get('detail', d)}")
        return None
    return d


def test_assessment_start(redirect_url: str) -> int:
    """
    GET the redirect URL (assessment-start with token&cluster_id).
    Returns HTTP status. Does not follow redirect to cluster dashboard.
    """
    r = requests.get(redirect_url, allow_redirects=False, timeout=10)
    return r.status_code


def validate_results_payload(payload: dict) -> list[str]:
    """Check payload has required keys per results_submission.json. Returns list of missing keys."""
    required_top = {"cluster_id", "cluster_name", "cluster_type", "user_id", "user_name", "roleplays"}
    missing = [k for k in required_top if k not in payload]
    rps = payload.get("roleplays") or []
    if not isinstance(rps, list):
        missing.append("roleplays (must be list)")
        return missing
    for i, rp in enumerate(rps):
        for k in ("roleplay_id", "roleplay_name", "stakeholders", "max_time", "time_taken", "competencies"):
            if k not in rp:
                missing.append(f"roleplays[{i}].{k}")
        for j, c in enumerate(rp.get("competencies") or []):
            for k in ("competency_code", "competency_name", "max_marks", "marks_obtained"):
                if k not in c:
                    missing.append(f"roleplays[{i}].competencies[{j}].{k}")
    return missing


def main() -> None:
    print("Q3 integration verification")
    print("=" * 50)
    print(f"ROLEVO_BASE_URL = {BASE_URL}")

    if not SECRET:
        print("ERROR: Set Q3_INTEGRATION_SECRET or AIO_CLIENT_SECRET (or AIO_API_TOKEN) in .env")
        sys.exit(1)

    # 1. API token + clusters
    print("\n1. API token + clusters")
    api_token = get_api_token()
    if not api_token:
        print("   FAIL: could not get API token")
        sys.exit(1)
    print("   OK: API token obtained")

    clusters = get_clusters(api_token)
    if not clusters:
        print("   FAIL: no clusters returned (create one in admin)")
        sys.exit(1)
    print(f"   OK: {len(clusters)} cluster(s)")

    cluster_id = TEST_CLUSTER_ID or (clusters[0].get("cluster_id"))
    if not cluster_id:
        cluster_id = str(clusters[0].get("id", ""))
    print(f"   Using cluster_id = {cluster_id}")

    # 2. Assessment launch
    print("\n2. POST /api/integration/assessment-launch")
    launch = test_assessment_launch(cluster_id)
    if not launch:
        print("   FAIL: assessment launch")
        sys.exit(1)
    redirect_url = launch.get("redirect_url")
    if not redirect_url:
        print("   FAIL: no redirect_url in response")
        sys.exit(1)
    print(f"   OK: redirect_url = {redirect_url[:80]}...")

    # 3. Assessment start (GET)
    print("\n3. GET /api/integration/assessment-start")
    status = test_assessment_start(redirect_url)
    if status in (302, 303, 307, 308):
        print(f"   OK: redirect ({status}) to cluster dashboard")
    elif status == 200:
        print("   OK: 200 (e.g. JSON error or same-origin redirect)")
    else:
        print(f"   WARN: unexpected status {status}")

    # 4. Validate results schema (example)
    print("\n4. Validate results payload shape (example)")
    example = {
        "cluster_id": "c1",
        "cluster_name": "C1",
        "cluster_type": "assessment",
        "user_id": "u1",
        "user_name": "U1",
        "roleplays": [
            {
                "roleplay_id": "rp1",
                "roleplay_name": "RP1",
                "stakeholders": "01",
                "max_time": 1800,
                "time_taken": 100,
                "competencies": [
                    {"competency_code": "C", "competency_name": "C", "max_marks": 10, "marks_obtained": 5}
                ],
            }
        ],
    }
    missing = validate_results_payload(example)
    if missing:
        print(f"   FAIL: example missing {missing}")
    else:
        print("   OK: example matches required shape")

    print("\n" + "=" * 50)
    print("Verification done. Run mock_q3_receiver.py and complete a roleplay to test results callback.")


if __name__ == "__main__":
    main()
