"""
Quick diagnostic script to check why reports aren't being sent
"""

import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

# Database connection
conn = mysql.connector.connect(
    host=os.getenv('DB_HOST', 'localhost'),
    user=os.getenv('DB_USER', 'root'),
    password=os.getenv('DB_PASSWORD'),
    database=os.getenv('DB_NAME', 'roleplay')
)

cur = conn.cursor()

# Check recent play sessions
print("=" * 60)
print("RECENT PLAY SESSIONS")
print("=" * 60)

cur.execute("""
    SELECT p.id, p.user_id, p.roleplay_id, p.start_time, p.status,
           u.email, r.name as roleplay_name
    FROM play p
    LEFT JOIN user u ON p.user_id = u.id
    LEFT JOIN roleplay r ON p.roleplay_id = r.id
    ORDER BY p.id DESC
    LIMIT 10
""")

results = cur.fetchall()

for row in results:
    play_id, user_id, roleplay_id, start_time, status, email, roleplay_name = row
    print(f"\nPlay ID: {play_id}")
    print(f"  User ID: {user_id}")
    print(f"  User Email: {email if email else 'NO EMAIL (user_id is NULL!)'}")
    print(f"  Roleplay ID: {roleplay_id}")
    print(f"  Roleplay Name: {roleplay_name if roleplay_name else '❌ ROLEPLAY NOT FOUND!'}")
    print(f"  Status: {status}")
    print(f"  Started: {start_time}")
    
    if user_id is None:
        print(f"  ⚠️  WARNING: user_id is NULL! Report cannot be sent.")
    
    if roleplay_name is None:
        print(f"  ⚠️  WARNING: roleplay_id '{roleplay_id}' does not exist in roleplay table!")

# Check roleplay IDs in database
print("\n" + "=" * 60)
print("AVAILABLE ROLEPLAYS")
print("=" * 60)

cur.execute("SELECT id, name FROM roleplay ORDER BY id LIMIT 10")
roleplays = cur.fetchall()

for rp_id, rp_name in roleplays:
    print(f"Roleplay ID: {rp_id} | Name: {rp_name}")

# Check SMTP configuration
print("\n" + "=" * 60)
print("SMTP CONFIGURATION CHECK")
print("=" * 60)

smtp_server = os.getenv('SMTP_SERVER')
smtp_port = os.getenv('SMTP_PORT')
smtp_username = os.getenv('SMTP_USERNAME')
smtp_password = os.getenv('SMTP_PASSWORD')

print(f"SMTP_SERVER: {smtp_server if smtp_server else '❌ NOT SET'}")
print(f"SMTP_PORT: {smtp_port if smtp_port else '❌ NOT SET'}")
print(f"SMTP_USERNAME: {smtp_username if smtp_username else '❌ NOT SET'}")
print(f"SMTP_PASSWORD: {'***' + smtp_password[-4:] if smtp_password else '❌ NOT SET'}")

if not all([smtp_server, smtp_port, smtp_username, smtp_password]):
    print("\n⚠️  SMTP not fully configured! Add these to your .env file:")
    print("""
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
    """)

# Check for users without email
print("\n" + "=" * 60)
print("USERS CHECK")
print("=" * 60)

cur.execute("SELECT id, email FROM user ORDER BY id DESC LIMIT 5")
users = cur.fetchall()

for user_id, email in users:
    print(f"User ID {user_id}: {email}")

cur.close()
conn.close()

print("\n" + "=" * 60)
print("DIAGNOSTIC COMPLETE")
print("=" * 60)
