"""
Migration: Add competency_file_path column to roleplay table
This allows each roleplay to have its own competency descriptions file
"""

import mysql.connector
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection details
host = os.getenv('DB_HOST', 'localhost')
user = os.getenv('DB_USER', 'root')
password = os.getenv('DB_PASSWORD', '')
database = os.getenv('DB_NAME', 'roleplay')

try:
    # Connect to database
    conn = mysql.connector.connect(
        host=host,
        user=user,
        password=password,
        database=database
    )
    cur = conn.cursor()
    
    print("Adding competency_file_path column to roleplay table...")
    
    # Add competency_file_path column
    cur.execute("""
        ALTER TABLE roleplay 
        ADD COLUMN competency_file_path VARCHAR(500) DEFAULT NULL
        AFTER image_file_path
    """)
    
    conn.commit()
    print("✅ Successfully added competency_file_path column")
    
    # Show current structure
    cur.execute("DESCRIBE roleplay")
    columns = cur.fetchall()
    print("\nCurrent roleplay table structure:")
    for col in columns:
        print(f"  - {col[0]} ({col[1]})")
    
    cur.close()
    conn.close()
    
except mysql.connector.Error as err:
    print(f"❌ Error: {err}")
    if 'Duplicate column name' in str(err):
        print("Note: Column might already exist")
except Exception as e:
    print(f"❌ Unexpected error: {e}")
