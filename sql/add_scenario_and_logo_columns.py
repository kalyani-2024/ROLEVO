"""
Add scenario_file_path and logo_path columns to roleplay table
"""

import mysql.connector as ms
import os
from dotenv import load_dotenv

load_dotenv()

# Database connection settings
host = os.getenv('DB_HOST', 'localhost')
user = os.getenv('DB_USERNAME', 'root')
password = os.getenv('DB_PASSWORD', '')
database = os.getenv('DB_NAME', 'roleplay')

try:
    # Connect to database
    conn = ms.connect(
        host=host,
        user=user,
        password=password,
        database=database
    )
    cur = conn.cursor()
    
    print("Connected to database successfully!")
    
    # Check if columns already exist
    cur.execute("""
        SELECT COLUMN_NAME 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_SCHEMA = %s 
        AND TABLE_NAME = 'roleplay' 
        AND COLUMN_NAME IN ('scenario_file_path', 'logo_path')
    """, (database,))
    
    existing_columns = [row[0] for row in cur.fetchall()]
    
    # Add scenario_file_path if it doesn't exist
    if 'scenario_file_path' not in existing_columns:
        print("Adding scenario_file_path column...")
        cur.execute("""
            ALTER TABLE roleplay 
            ADD COLUMN scenario_file_path VARCHAR(500) DEFAULT NULL
        """)
        print("✓ scenario_file_path column added successfully!")
    else:
        print("✓ scenario_file_path column already exists")
    
    # Add logo_path if it doesn't exist
    if 'logo_path' not in existing_columns:
        print("Adding logo_path column...")
        cur.execute("""
            ALTER TABLE roleplay 
            ADD COLUMN logo_path VARCHAR(500) DEFAULT NULL
        """)
        print("✓ logo_path column added successfully!")
    else:
        print("✓ logo_path column already exists")
    
    # Commit changes
    conn.commit()
    print("\n✅ Migration completed successfully!")
    
except ms.Error as err:
    print(f"❌ Database error: {err}")
except Exception as e:
    print(f"❌ Error: {e}")
finally:
    if 'conn' in locals() and conn.is_connected():
        cur.close()
        conn.close()
        print("Database connection closed.")
