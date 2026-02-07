"""
Mock Q3 receiver for local integration testing.

Exposes:
  POST /api/receive-cluster-metadata   (cluster create/update from Rolevo)
  POST /api/receive-assessment-results (results when user completes roleplay)

Run: python scripts/mock_q3_receiver.py
Then set Q3_BASE_URL=http://127.0.0.1:5999 and AIO_CALLBACK_URL=http://127.0.0.1:5999/api/receive-assessment-results
(or use results_url in assessment-launch) and create/update clusters / complete roleplays.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

# Project root
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from flask import Flask, request, jsonify
except ImportError:
    print("Install Flask: pip install flask")
    sys.exit(1)

app = Flask(__name__)
PORT = 5999
HOST = "0.0.0.0"


def _log(label: str, data: dict) -> None:
    ts = datetime.utcnow().strftime("%H:%M:%S")
    print(f"\n[{ts}] === {label} ===")
    print(json.dumps(data, indent=2, default=str))
    print()


@app.route("/api/receive-cluster-metadata", methods=["POST"])
def receive_cluster_metadata():
    """Mock Q3 endpoint: cluster metadata sync (Rolevo -> Q3)."""
    try:
        data = request.get_json(force=True, silent=True) or {}
    except Exception:
        data = {}
    _log("POST /api/receive-cluster-metadata", data)
    return jsonify({
        "success": True,
        "cluster_id": data.get("cluster_id", "unknown"),
        "message": "Cluster metadata received successfully",
    }), 200


@app.route("/api/receive-assessment-results", methods=["POST"])
def receive_assessment_results():
    """Mock Q3 endpoint: assessment results (Rolevo -> Q3)."""
    try:
        data = request.get_json(force=True, silent=True) or {}
    except Exception:
        data = {}
    _log("POST /api/receive-assessment-results", data)
    return jsonify({
        "success": True,
        "user_id": data.get("user_id"),
        "cluster_id": data.get("cluster_id"),
        "message": "Results received successfully",
    }), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "mock": "q3"}), 200


if __name__ == "__main__":
    print(f"Mock Q3 receiver: http://{HOST}:{PORT}")
    print("  POST /api/receive-cluster-metadata")
    print("  POST /api/receive-assessment-results")
    print("\nSet Q3_BASE_URL and AIO_CALLBACK_URL (or results_url) accordingly.\n")
    app.run(host=HOST, port=PORT, debug=False, use_reloader=False)
