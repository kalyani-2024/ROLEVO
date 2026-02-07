
import sys
import os

# Redirect stdout to a file
log_file = open('debug_log.txt', 'w', encoding='utf-8')
sys.stdout = log_file
sys.stderr = log_file

print("Starting debug script...")

try:
    from app import app
    from app.queries import get_all_users, get_cluster_users, get_clusters, create_cluster, assign_cluster_to_user

    # Set up context
    ctx = app.app_context()
    ctx.push()

    print("--- DEBUGGING DATA ---")

    # 1. Get all users
    users = get_all_users()
    print(f"Total Users: {len(users) if users else 0}")
    if users:
        print(f"First user sample: {users[0]}")
        user_id = users[0][0]
        print(f"User ID: {user_id}, type: {type(user_id)}")

    # 2. Get clusters
    clusters = get_clusters()
    print(f"Total Clusters: {len(clusters) if clusters else 0}")

    if clusters:
        cluster_id = clusters[0][0]
        print(f"Testing with Cluster ID: {cluster_id} (type: {type(cluster_id)})")
        
        # 3. Get cluster users
        cluster_users = get_cluster_users(cluster_id)
        print(f"Cluster Users: {len(cluster_users) if cluster_users else 0}")
        
        if cluster_users:
            print(f"First cluster user sample: {cluster_users[0]}")
            c_user_id = cluster_users[0][0]
            print(f"Cluster User ID: {c_user_id}, type: {type(c_user_id)}")
            
            assigned_user_ids = [u[0] for u in cluster_users]
            print(f"Assigned User IDs: {assigned_user_ids}")
            
            # Check membership
            test_user_id = cluster_users[0][0]
            print(f"Is {test_user_id} in {assigned_user_ids}? {test_user_id in assigned_user_ids}")
            
            # Check user from all users list
            matching_user = next((u for u in users if u[0] == test_user_id), None)
            if matching_user:
                print(f"User from main list: {matching_user}")
                m_user_id = matching_user[0]
                print(f"Main User ID: {m_user_id}, type: {type(m_user_id)}")
                print(f"Is {m_user_id} in {assigned_user_ids}? {m_user_id in assigned_user_ids}")
        else:
            print("No users assigned to this cluster.")
            # Verify with raw query if needed, or check logic
            
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

print("Debug script finished.")
log_file.close()
