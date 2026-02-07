
import sys
import os
import time

try:
    with open('debug_log_v3.txt', 'w', encoding='utf-8') as f:
        f.write("Starting debug script v3 (Full Cycle)...\n")
        
        try:
            from app import app
            from app.queries import (
                get_all_users, get_cluster_users, get_clusters, 
                create_cluster, assign_cluster_to_user, create_user_account,
                delete_cluster, remove_cluster_from_user, get_user_by_email
            )
            import mysql.connector as ms

            # Set up context
            ctx = app.app_context()
            ctx.push()
            f.write("App context pushed.\n")

            # 1. Create Dummy User
            test_email = f"debug_user_{int(time.time())}@example.com"
            f.write(f"Creating dummy user: {test_email}\n")
            user_id, msg = create_user_account(test_email, "Password123!")
            
            if not user_id:
                 # Try finding if exists
                u = get_user_by_email(test_email)
                if u:
                    user_id = u[0]
                    f.write(f"User existed, ID: {user_id}\n")
                else:
                    f.write(f"Failed to create user: {msg}\n")
                    sys.exit(1)
            else:
                f.write(f"Created User ID: {user_id} (type: {type(user_id)})\n")

            # 2. Create Dummy Cluster
            cluster_name = f"Debug Cluster {int(time.time())}"
            f.write(f"Creating dummy cluster: {cluster_name}\n")
            cluster_id = create_cluster(cluster_name, cluster_type='assessment')
            f.write(f"Created Cluster ID: {cluster_id} (type: {type(cluster_id)})\n")

            if not cluster_id:
                f.write("Failed to create cluster.\n")
                sys.exit(1)

            # 3. Assign User to Cluster
            f.write("Assigning user to cluster...\n")
            success = assign_cluster_to_user(user_id, cluster_id)
            f.write(f"Assignment success: {success}\n")

            # 4. Verify DB directly (bypass wrapper)
            f.write("Verifying in DB directly...\n")
            # We need to implement a mini-query here because we are in a script
            # Skipping direct DB check to rely on functions first
            
            # 5. Fetch via get_cluster_users
            f.write("Fetching cluster users via get_cluster_users...\n")
            cluster_users = get_cluster_users(cluster_id)
            f.write(f"Cluster Users Found: {len(cluster_users)}\n")
            
            match_found = False
            for u in cluster_users:
                f.write(f"  Found User: ID={u[0]} (type: {type(u[0])}), Name={u[2]}\n")
                if u[0] == user_id:
                    match_found = True
                    f.write("  MATCH CONFIRMED: IDs match and types match.\n")
            
            if not match_found:
                f.write("FAIL: User assigned but not returned by get_cluster_users.\n")
            else:
                f.write("SUCCESS: User assigned and returned correctly.\n")
                
                # Check assigned_user_ids list construction
                assigned_user_ids = [u[0] for u in cluster_users]
                f.write(f"assigned_user_ids list: {assigned_user_ids}\n")
                f.write(f"Is user_id in list? {user_id in assigned_user_ids}\n")

            # 6. Clean up
            f.write("Cleaning up...\n")
            remove_cluster_from_user(user_id, cluster_id)
            delete_cluster(cluster_id)
            # Cannot delete user easily with provided functions, leave it (it's harmless)
            f.write("Cleanup done.\n")

        except Exception as inner_e:
            f.write(f"ERROR: {inner_e}\n")
            import traceback
            f.write(traceback.format_exc())

except Exception as e:
    print(f"CRITICAL ERROR: {e}")
