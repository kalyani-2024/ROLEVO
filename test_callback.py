"""
Dynamic test script to verify callback function works with REAL data from database.
This will test the actual build_result_payload function.
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

def test_callback_with_real_data():
    """Test sending a callback using the actual build_result_payload function"""
    import requests
    from flask import Flask
    
    # Create minimal Flask app for session context
    app = Flask(__name__)
    app.secret_key = os.getenv('SECRET_KEY', 'test-secret')
    
    callback_url = "https://webhook.site/e1d69bf2-6cb7-4856-83a1-e394dce6cc33"
    
    with app.app_context():
        from flask import session
        
        # Get the most recent completed play from database
        import mysql.connector
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME', 'roleplay')
        )
        cur = conn.cursor(dictionary=True)
        
        # Get most recent completed play
        cur.execute("""
            SELECT p.id as play_id, p.user_id, p.roleplay_id, p.cluster_id,
                   p.start_time, p.end_time, p.status
            FROM play p
            WHERE p.status = 'completed'
            ORDER BY p.end_time DESC
            LIMIT 1
        """)
        play = cur.fetchone()
        
        if not play:
            print("❌ No completed plays found in database!")
            print("   Complete a roleplay first, then run this test.")
            return
        
        print(f"📋 Found play: {play}")
        
        # Set up session context
        with app.test_request_context():
            from flask import session as test_session
            test_session['cluster_id'] = play['cluster_id']
            test_session['aio_user_id'] = f"TEST-{play['user_id']}"
            
            # Import and call the real build_result_payload function
            from app.api_integration import build_result_payload, generate_signature
            
            # Build the real payload
            payload = build_result_payload(
                play_id=play['play_id'],
                user_id=play['user_id'],
                roleplay_id=play['roleplay_id'],
                scores={}  # Empty scores, will be populated from DB
            )
            
            print("\n📦 REAL Payload from build_result_payload:")
            import json
            print(json.dumps(payload, indent=2, default=str))
            
            print(f"\n🚀 Sending to: {callback_url}")
            
            try:
                response = requests.post(
                    callback_url,
                    json=payload,
                    headers={'Content-Type': 'application/json'},
                    timeout=30
                )
                
                print(f"\n✅ Response Status: {response.status_code}")
                
                if response.ok:
                    print("\n🎉 SUCCESS! Real callback sent!")
                    print("👉 Check webhook.site to see the actual payload")
                else:
                    print(f"\n❌ FAILED: {response.text[:200]}")
                    
            except Exception as e:
                print(f"\n❌ ERROR: {e}")
        
        cur.close()
        conn.close()

if __name__ == "__main__":
    test_callback_with_real_data()
