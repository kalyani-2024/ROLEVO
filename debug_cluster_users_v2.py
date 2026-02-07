
try:
    with open('debug_log_v2.txt', 'w', encoding='utf-8') as f:
        f.write("Starting debug script v2...\n")
        
        try:
            from app import app
            from app.queries import get_all_users, get_cluster_users, get_clusters, create_cluster, assign_cluster_to_user

            # Set up context
            ctx = app.app_context()
            ctx.push()
            f.write("App context pushed.\n")

            f.write("--- DEBUGGING DATA ---\n")

            # 1. Get all users
            users = get_all_users()
            f.write(f"Total Users: {len(users) if users else 0}\n")
            if users:
                user_id = users[0][0]
                f.write(f"First user ID: {user_id}, type: {type(user_id)}\n")

            # 2. Get clusters
            clusters = get_clusters()
            f.write(f"Total Clusters: {len(clusters) if clusters else 0}\n")

            if clusters:
                cluster_id = clusters[0][0]
                f.write(f"Testing with Cluster ID: {cluster_id} (type: {type(cluster_id)})\n")
                
                # 3. Get cluster users
                cluster_users = get_cluster_users(cluster_id)
                f.write(f"Cluster Users: {len(cluster_users) if cluster_users else 0}\n")
                
                if cluster_users:
                    c_user_id = cluster_users[0][0]
                    f.write(f"First cluster user ID: {c_user_id}, type: {type(c_user_id)}\n")
                    
                    assigned_user_ids = [u[0] for u in cluster_users]
                    f.write(f"Assigned User IDs: {assigned_user_ids}\n")
                    
                    # Test membership
                    test_id = assigned_user_ids[0]
                    f.write(f"Is {test_id} (type {type(test_id)}) in list? {test_id in assigned_user_ids}\n")
                    
                    # Check against all users
                    found = False
                    for u in users:
                        if u[0] == test_id:
                            f.write(f"Match found in users list! ID: {u[0]} type: {type(u[0])}\n")
                            found = True
                            break
                    if not found:
                        f.write(f"WARNING: ID {test_id} not found in users list!\n")
                else:
                    f.write("No users assigned to this cluster.\n")
            else:
                f.write("No clusters found.\n")
                
        except Exception as inner_e:
            f.write(f"ERROR: {inner_e}\n")
            import traceback
            f.write(traceback.format_exc())

except Exception as e:
    # Fallback if file open fails
    print(f"CRITICAL ERROR: {e}")
