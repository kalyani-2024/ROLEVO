"""
Run this script to create the roleplay_characters table in your database
This table stores character names and their genders for voice generation
"""

import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

try:
    conn = mysql.connector.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME', 'roleplay')
    )
    
    cursor = conn.cursor()
    
    # Create the table
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS roleplay_characters (
        id INT AUTO_INCREMENT PRIMARY KEY,
        roleplay_id INT NOT NULL,
        character_name VARCHAR(100) NOT NULL,
        gender ENUM('male', 'female') NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (roleplay_id) REFERENCES roleplay(id) ON DELETE CASCADE,
        UNIQUE KEY unique_roleplay_character (roleplay_id, character_name)
    );
    """
    
    cursor.execute(create_table_sql)
    conn.commit()
    
    print("✅ Table 'roleplay_characters' created successfully!")
    print("\nYou can now add character gender mappings through:")
    print("1. Admin panel (when uploading/editing roleplays)")
    print("2. Direct SQL: INSERT INTO roleplay_characters (roleplay_id, character_name, gender) VALUES (1, 'CharacterName', 'male');")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Error creating table: {e}")
