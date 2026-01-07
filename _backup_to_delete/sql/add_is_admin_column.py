import mysql.connector

# Add is_admin column to user table

try:
    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='Kalkamal2005!',
        database='roleplay'
    )
    cursor = conn.cursor()
    
    print("Adding is_admin column to user table...")
    
    # Check if column already exists
    cursor.execute("DESCRIBE user")
    columns = [col[0] for col in cursor.fetchall()]
    
    if 'is_admin' not in columns:
        # Add is_admin column with default value 0
        cursor.execute("ALTER TABLE user ADD COLUMN is_admin TINYINT(1) DEFAULT 0 AFTER password")
        conn.commit()
        print("✓ is_admin column added successfully")
        
        # Optionally, set first user as admin
        cursor.execute("SELECT id, email FROM user ORDER BY id LIMIT 1")
        first_user = cursor.fetchone()
        if first_user:
            print(f"\nFirst user found: ID={first_user[0]}, Email={first_user[1]}")
            make_admin = input("Do you want to make this user an admin? (y/n): ")
            if make_admin.lower() == 'y':
                cursor.execute("UPDATE user SET is_admin = 1 WHERE id = %s", (first_user[0],))
                conn.commit()
                print(f"✓ User {first_user[1]} is now an admin")
    else:
        print("✓ is_admin column already exists")
    
    # Show current structure
    print("\nCurrent user table structure:")
    cursor.execute("DESCRIBE user")
    for col in cursor.fetchall():
        print(f"  {col[0]:15} {col[1]:20} Null:{col[2]} Key:{col[3]} Default:{col[4]}")
    
    # Show all users with their admin status
    print("\nCurrent users:")
    cursor.execute("SELECT id, email, is_admin FROM user")
    users = cursor.fetchall()
    if users:
        print(f"  {'ID':<5} {'Email':<30} {'Admin':<10}")
        print("  " + "-" * 50)
        for user in users:
            admin_status = "Yes" if user[2] == 1 else "No"
            print(f"  {user[0]:<5} {user[1]:<30} {admin_status:<10}")
    else:
        print("  No users found")
    
    cursor.close()
    conn.close()
    
    print("\n✓ Migration completed successfully!")
    
except mysql.connector.Error as e:
    print(f"✗ Database error: {e}")
except Exception as e:
    print(f"✗ Error: {e}")
