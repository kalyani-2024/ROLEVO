"""
Test script to verify cluster type detection
Run this to check if your clusters are set up correctly
"""

import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def test_cluster_detection():
    conn = mysql.connector.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME', 'roleplay')
    )
    cur = conn.cursor()
    
    print("\n" + "="*80)
    print("🔍 CLUSTER TYPE DETECTION TEST")
    print("="*80)
    
    # Get all clusters
    cur.execute("SELECT id, name, type FROM roleplay_cluster ORDER BY id")
    clusters = cur.fetchall()
    
    print(f"\n📋 Found {len(clusters)} cluster(s) in database:\n")
    for cluster in clusters:
        print(f"   Cluster ID: {cluster[0]}")
        print(f"   Name: {cluster[1]}")
        print(f"   Type: '{cluster[2]}'")
        print(f"   Type is 'assessment': {cluster[2] == 'assessment'}")
        print(f"   Type is 'training': {cluster[2] == 'training'}")
        
        # Get roleplays in this cluster
        cur.execute("""
            SELECT r.id, r.name 
            FROM roleplay r
            JOIN cluster_roleplay cr ON r.id = cr.roleplay_id
            WHERE cr.cluster_id = %s
            ORDER BY cr.order_sequence
        """, (cluster[0],))
        roleplays = cur.fetchall()
        
        print(f"   Roleplays in cluster: {len(roleplays)}")
        for rp in roleplays:
            print(f"      - {rp[0]}: {rp[1]}")
        print()
    
    # Check for roleplays in multiple clusters
    cur.execute("""
        SELECT cr.roleplay_id, r.name, COUNT(DISTINCT cr.cluster_id) as cluster_count
        FROM cluster_roleplay cr
        JOIN roleplay r ON cr.roleplay_id = r.id
        GROUP BY cr.roleplay_id, r.name
        HAVING cluster_count > 1
    """)
    multi_cluster = cur.fetchall()
    
    if multi_cluster:
        print("\n⚠️  WARNING: The following roleplays exist in multiple clusters:")
        print("   (Make sure cluster_id is passed correctly in the URL!)\n")
        for rp in multi_cluster:
            print(f"   {rp[0]}: {rp[1]} (in {rp[2]} clusters)")
            
            # Show which clusters
            cur.execute("""
                SELECT rc.id, rc.name, rc.type
                FROM roleplay_cluster rc
                JOIN cluster_roleplay cr ON rc.id = cr.cluster_id
                WHERE cr.roleplay_id = %s
            """, (rp[0],))
            clusters_for_rp = cur.fetchall()
            for c in clusters_for_rp:
                print(f"      → Cluster {c[0]}: {c[1]} (type: {c[2]})")
            print()
    
    print("="*80)
    print("✅ Test complete!")
    print("="*80 + "\n")
    
    cur.close()
    conn.close()

if __name__ == '__main__':
    test_cluster_detection()
