"""Quick script to check 16PF analysis data in database"""
import mysql.connector
import json
import os
from dotenv import load_dotenv

load_dotenv()

host = os.getenv('DB_HOST', 'localhost')
user = os.getenv('DB_USER', 'root')
password = os.getenv('DB_PASSWORD')
database = os.getenv('DB_NAME', 'roleplay')

conn = mysql.connector.connect(
    host=host,
    user=user,
    password=password,
    database=database
)
cur = conn.cursor(dictionary=True)

print("=== Checking pf16_analysis_results table ===\n")

cur.execute('SELECT id, play_id, status, raw_response, personality_scores, composite_scores FROM pf16_analysis_results ORDER BY id DESC LIMIT 5')
results = cur.fetchall()

for r in results:
    print(f"=== ID: {r['id']}, play_id: {r['play_id']}, status: {r['status']} ===")
    
    if r['raw_response']:
        try:
            raw = json.loads(r['raw_response'])
            print(f"RAW RESPONSE KEYS: {list(raw.keys()) if isinstance(raw, dict) else 'Not a dict'}")
            print(f"RAW RESPONSE FULL: {json.dumps(raw, indent=2)}")
        except:
            print(f"RAW RESPONSE (not JSON): {r['raw_response'][:500]}")
    else:
        print("RAW RESPONSE: None")
        
    if r['personality_scores']:
        try:
            ps = json.loads(r['personality_scores'])
            print(f"PERSONALITY SCORES ({len(ps)} items): {json.dumps(ps, indent=2)}")
        except:
            print(f"PERSONALITY SCORES (not JSON): {r['personality_scores'][:500]}")
    else:
        print("PERSONALITY SCORES: None")
        
    if r['composite_scores']:
        try:
            cs = json.loads(r['composite_scores'])
            print(f"COMPOSITE SCORES ({len(cs)} items): {json.dumps(cs, indent=2)}")
        except:
            print(f"COMPOSITE SCORES (not JSON): {r['composite_scores'][:500]}")
    else:
        print("COMPOSITE SCORES: None")
        
    print("\n" + "="*50 + "\n")

cur.close()
conn.close()
