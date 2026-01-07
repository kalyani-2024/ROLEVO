"""
Migration script to add difficulty_level to roleplay_config table
"""

import mysql.connector as ms
import sys
import os
from dotenv import load_dotenv

load_dotenv()

host = os.getenv('DB_HOST', 'localhost')
user = os.getenv('DB_USER', 'root')
password = os.getenv('DB_PASSWORD')
database = os.getenv('DB_NAME', 'roleplay')

def add_difficulty_level():
    try:
        conn = ms.connect(host=host, user=user, password=password, database=database)
        cur = conn.cursor()
        
        print("Adding difficulty_level column to roleplay_config table...")
        
        # Check if column already exists
        cur.execute("SHOW COLUMNS FROM roleplay_config LIKE 'difficulty_level'")
        if cur.fetchone():
            print("Column 'difficulty_level' already exists. Skipping.")
            return
        
        # Add difficulty_level column
        cur.execute("""
            ALTER TABLE roleplay_config 
            ADD COLUMN difficulty_level ENUM('easy', 'medium', 'hard') DEFAULT 'easy' 
            AFTER voice_assessment_enabled
        """)
        
        conn.commit()
        print("✅ Successfully added difficulty_level column!")
        print("   Default value: 'easy'")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.rollback()
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    add_difficulty_level()
