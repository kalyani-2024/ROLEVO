"""
Migration script to change roleplay.id from VARCHAR to AUTO_INCREMENT INTEGER
This allows roleplay IDs to be auto-generated
"""

import mysql.connector as ms
import sys
import os

# Add parent directory to path to import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import host, user, password, database

def alter_roleplay_id():
    try:
        conn = ms.connect(host=host, user=user, password=password, database=database)
        cur = conn.cursor()
        
        print("Starting migration to change roleplay.id to AUTO_INCREMENT...")
        
        # Step 1: Check current table structure
        cur.execute("DESCRIBE roleplay")
        columns = cur.fetchall()
        print("\nCurrent roleplay table structure:")
        for col in columns:
            print(f"  {col}")
        
        # Step 2: Create a temporary new table with auto-increment ID
        print("\nCreating new table with auto-increment ID...")
        cur.execute('''
            CREATE TABLE roleplay_new (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(1000) NOT NULL,
                file_path VARCHAR(500) NOT NULL,
                image_file_path VARCHAR(500) NOT NULL,
                scenario VARCHAR(2000) NOT NULL,
                person_name VARCHAR(1000) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        ''')
        
        # Step 3: Copy data from old table to new table
        print("Copying existing data to new table...")
        cur.execute('''
            INSERT INTO roleplay_new (id, name, file_path, image_file_path, scenario, person_name, created_at, updated_at)
            SELECT 
                CAST(id AS UNSIGNED) as id,
                name, 
                file_path, 
                image_file_path, 
                scenario, 
                person_name,
                created_at,
                updated_at
            FROM roleplay
            WHERE id REGEXP '^[0-9]+$'
        ''')
        rows_copied = cur.rowcount
        print(f"Copied {rows_copied} rows with numeric IDs")
        
        # Step 4: Get the maximum ID to set AUTO_INCREMENT start value
        cur.execute("SELECT MAX(id) FROM roleplay_new")
        max_id = cur.fetchone()[0]
        if max_id:
            next_id = max_id + 1
            print(f"Setting AUTO_INCREMENT to start at {next_id}")
            cur.execute(f"ALTER TABLE roleplay_new AUTO_INCREMENT = {next_id}")
        
        # Step 5: Drop foreign key constraints that reference roleplay table
        print("\nHandling foreign key constraints...")
        
        # Disable foreign key checks temporarily
        cur.execute("SET FOREIGN_KEY_CHECKS = 0")
        
        # Step 6: Rename tables
        print("Renaming tables...")
        cur.execute("DROP TABLE roleplay")
        cur.execute("RENAME TABLE roleplay_new TO roleplay")
        
        # Step 7: Re-enable foreign key checks
        cur.execute("SET FOREIGN_KEY_CHECKS = 1")
        
        # Step 8: Verify new structure
        cur.execute("DESCRIBE roleplay")
        columns = cur.fetchall()
        print("\nNew roleplay table structure:")
        for col in columns:
            print(f"  {col}")
        
        # Commit changes
        conn.commit()
        print("\n✅ Migration completed successfully!")
        print(f"   Roleplay IDs will now be auto-generated starting from {next_id if max_id else 1}")
        
    except Exception as e:
        print(f"\n❌ Error during migration: {str(e)}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.rollback()
        sys.exit(1)
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    print("="*80)
    print("ROLEPLAY ID AUTO-INCREMENT MIGRATION")
    print("="*80)
    print("\nThis script will:")
    print("  1. Create a new roleplay table with AUTO_INCREMENT ID")
    print("  2. Copy existing data (numeric IDs only)")
    print("  3. Replace the old table with the new one")
    print("\n⚠️  WARNING: This will drop non-numeric roleplay IDs!")
    print("="*80)
    
    response = input("\nDo you want to continue? (yes/no): ")
    if response.lower() in ['yes', 'y']:
        alter_roleplay_id()
    else:
        print("Migration cancelled.")
