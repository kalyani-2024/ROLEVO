import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

# Connect to database
conn = mysql.connector.connect(
    host=os.getenv('DB_HOST', 'localhost'),
    user=os.getenv('DB_USER', 'root'),
    password=os.getenv('DB_PASSWORD'),
    database=os.getenv('DB_NAME', 'roleplay')
)

cursor = conn.cursor()

# First, let's see all roleplays and their data
print("\n=== CURRENT ROLEPLAY DATA ===")
cursor.execute("SELECT id, name, competency_file_path, scenario_file_path, logo_path, created_at, updated_at FROM roleplay")
for row in cursor.fetchall():
    print(f"ID: {row[0]}")
    print(f"  Name: {row[1]}")
    print(f"  Competency: {row[2]}")
    print(f"  Scenario: {row[3]}")
    print(f"  Logo: {row[4]}")
    print(f"  Created: {row[5]}")
    print(f"  Updated: {row[6]}")
    print()

# Fix the Flavia roleplay - set empty strings for missing file paths
print("\n=== FIXING FLAVIA ROLEPLAY ===")
cursor.execute("""
    UPDATE roleplay 
    SET 
        competency_file_path = NULL,
        scenario_file_path = NULL,
        logo_path = NULL
    WHERE name LIKE '%Flavia%'
""")
conn.commit()
print("Updated Flavia roleplay")

# Verify the fix
print("\n=== AFTER FIX ===")
cursor.execute("SELECT id, name, competency_file_path, scenario_file_path, logo_path, created_at, updated_at FROM roleplay WHERE name LIKE '%Flavia%'")
for row in cursor.fetchall():
    print(f"ID: {row[0]}")
    print(f"  Name: {row[1]}")
    print(f"  Competency: {row[2]}")
    print(f"  Scenario: {row[3]}")
    print(f"  Logo: {row[4]}")
    print(f"  Created: {row[5]}")
    print(f"  Updated: {row[6]}")

cursor.close()
conn.close()

print("\n=== DONE ===")
print("Now refresh the edit page in your browser to see the fix!")
