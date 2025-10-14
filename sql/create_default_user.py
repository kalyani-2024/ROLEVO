import mysql.connector

try:
    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='Kalkamal2005!',
        database='roleplay'
    )
    cursor = conn.cursor()
    
    # Check if user 1 exists
    cursor.execute("SELECT id FROM user WHERE id = 1")
    user_exists = cursor.fetchone()
    
    if not user_exists:
        print("User 1 does not exist. Creating default user...")
        cursor.execute("""
            INSERT INTO user (id, email, password) 
            VALUES (1, 'admin@example.com', 'default_password_hash')
        """)
        print("Created default user with id=1")
    else:
        print("User 1 already exists")
    
    # Let's also check what users currently exist
    cursor.execute("SELECT id, email FROM user")
    users = cursor.fetchall()
    print(f"\nCurrent users in database:")
    for user in users:
        print(f"  ID: {user[0]}, Email: {user[1]}")
    
    conn.commit()
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()