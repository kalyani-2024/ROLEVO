"""
Verify Q3 JSON Payloads by sending real data to Webhook.site.
Tests:
1. Cluster Metadata Sync
2. Assessment Result Callback
"""
import os
import sys
from flask import Flask, session

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

# Configuration
WEBHOOK_URL = "https://webhook.site/e1d69bf2-6cb7-4856-83a1-e394dce6cc33"

def verify_payloads():
    app = Flask(__name__)
    app.secret_key = 'test-secret'
    
    with app.app_context():
        # Setup Environment for Testing
        # 1. Point Q3_BASE_URL to Webhook to capture sync call
        # The code does: url = f"{base}/api/receive-cluster-metadata"
        # So we set base to the webhook url, handling the path logic
        os.environ['Q3_BASE_URL'] = WEBHOOK_URL.rstrip('/') 
        # Note: This will result in POST to .../api/receive-cluster-metadata which webhook.site captures
        
        # 2. Point AIO_CALLBACK_URL to Webhook for result callback
        os.environ['AIO_CALLBACK_URL'] = WEBHOOK_URL
        
        print(f"🎯 Target Webhook: {WEBHOOK_URL}")
        
        # --- TEST 1: Cluster Metadata Sync ---
        print("\n[1/2] Testing Cluster Metadata Sync...")
        from app.api_integration import sync_cluster_metadata_to_q3
        
        # Get a valid cluster ID from DB
        import mysql.connector
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME', 'roleplay')
        )
        cur = conn.cursor()
        cur.execute("SELECT id FROM roleplay_cluster LIMIT 1")
        cluster = cur.fetchone()
        
        if cluster:
            print(f"   Syncing Cluster ID: {cluster[0]}")
            try:
                # Mock requests.post to print url if needed, but we rely on real call
                resp = sync_cluster_metadata_to_q3(cluster[0])
                if resp is False: # It might return False if request fails or non-200. Webhook.site returns 200 usually.
                    pass # check function return logic
            except Exception as e:
                print(f"   ❌ Error: {e}")
            print("   ✅ Sync attempted. Check Webhook for '/api/receive-cluster-metadata'")
        else:
            print("   ❌ No clusters found to sync.")

        # --- TEST 2: Result Callback ---
        print("\n[2/2] Testing Result Callback...")
        from app.api_integration import send_results_to_aio, build_result_payload
        
        # Get a valid completed play
        cur.execute("""
            SELECT id, user_id, roleplay_id, cluster_id 
            FROM play 
            WHERE status = 'completed' 
            ORDER BY end_time DESC LIMIT 1
        """)
        play = cur.fetchone()
        cur.close()
        conn.close()
        
        if play:
            play_id = play[0]
            user_id = play[1]
            roleplay_id = play[2]
            cluster_id = play[3]
            
            print(f"   Sending results for Play ID: {play_id}")
            
            # Setup session for build_result_payload
            with app.test_request_context():
                session['cluster_id'] = cluster_id
                session['aio_user_id'] = f"Q3-USER-{user_id}" # Mock External ID
                # Mock callback_url in session to be sure
                session['callback_url'] = WEBHOOK_URL
                
                try:
                    # Pass some mock scores
                    scores = {
                        'overall_score': 85,
                        'feedback': 'Good job',
                        '16pf_analysis': {'enabled': True, 'score': 7.5}
                    }
                    
                    send_results_to_aio(play_id, user_id, roleplay_id, scores)
                    print("   ✅ Callback sent. Check Webhook for the JSON payload.")
                except Exception as e:
                    print(f"   ❌ Error: {e}")
        else:
            print("   ❌ No completed plays found.")

if __name__ == "__main__":
    verify_payloads()
