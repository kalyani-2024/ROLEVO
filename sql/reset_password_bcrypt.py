import mysql.connector
import bcrypt

# Reset admin password using bcrypt directly

try:
    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='Kalkamal2005!',
        database='roleplay'
    )
    cursor = conn.cursor()
    
    print("Admin Password Reset Tool\n")
    print("=" * 50)
    
    # Show all admin users
    cursor.execute("SELECT id, email FROM user WHERE is_admin = 1")
    admins = cursor.fetchall()
    
    if not admins:
        print("No admin users found!")
        conn.close()
        exit()
    
    print("\nAdmin users:")
    for admin in admins:
        print(f"  ID: {admin[0]}, Email: {admin[1]}")
    
    print("\n" + "=" * 50)
    
    # Get admin to reset
    admin_email = input("\nEnter admin email to reset password: ").strip()
    
    # Check if admin exists
    cursor.execute("SELECT id, email FROM user WHERE email = %s AND is_admin = 1", (admin_email,))
    admin = cursor.fetchone()
    
    if not admin:
        print(f"Error: Admin user '{admin_email}' not found!")
        conn.close()
        exit()
    
    # Get new password
    new_password = input("Enter new password (min 6 characters): ").strip()
    
    if len(new_password) < 6:
        print("Error: Password must be at least 6 characters!")
        conn.close()
        exit()
    
    confirm_password = input("Confirm new password: ").strip()
    
    if new_password != confirm_password:
        print("Error: Passwords do not match!")
        conn.close()
        exit()
    
    # Hash the new password using bcrypt directly
    print("\nHashing password...")
    password_bytes = new_password.encode('utf-8')
    salt = bcrypt.gensalt(rounds=12)
    hashed_password = bcrypt.hashpw(password_bytes, salt)
    hashed_password_str = hashed_password.decode('utf-8')
    
    # Update password in database
    cursor.execute("UPDATE user SET password = %s WHERE email = %s", (hashed_password_str, admin_email))
    conn.commit()
    
    print(f"\n✓ Password successfully reset for {admin_email}")
    print("\nYou can now login with:")
    print(f"  Email: {admin_email}")
    print(f"  Password: {new_password}")
    print("\nPlease remember this password!")
    
    cursor.close()
    conn.close()
    
except mysql.connector.Error as e:
    print(f"✗ Database error: {e}")
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
