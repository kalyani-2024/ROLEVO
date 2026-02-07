"""
Script to clear all roleplays from the PythonAnywhere database.
Run this script to delete ALL roleplays and their related data.

WARNING: This will permanently delete all roleplay data!
"""

import os
import mysql.connector as ms
from dotenv import load_dotenv

load_dotenv()

# Database connection details (from .env file)
host = os.getenv('DB_HOST', 'localhost')
user = os.getenv('DB_USER', 'root')
password = os.getenv('DB_PASSWORD')
database = os.getenv('DB_NAME', 'roleplay')

def clear_all_roleplays():
    """Delete all roleplays and their related data from the database."""
    
    print(f"\n{'='*60}")
    print("⚠️  WARNING: This will DELETE ALL ROLEPLAYS from the database!")
    print(f"{'='*60}")
    print(f"\nDatabase: {database}")
    print(f"Host: {host}")
    print(f"User: {user}")
    
    # Confirm before proceeding
    confirm = input("\nType 'DELETE ALL' to confirm: ")
    if confirm != 'DELETE ALL':
        print("❌ Operation cancelled.")
        return
    
    try:
        with ms.connect(host=host, user=user, password=password, database=database) as dbconn:
            cursor = dbconn.cursor()
            
            # Get count of roleplays before deletion
            cursor.execute("SELECT COUNT(*) FROM roleplay")
            count = cursor.fetchone()[0]
            print(f"\n📊 Found {count} roleplays to delete...")
            
            if count == 0:
                print("✅ No roleplays to delete.")
                return
            
            # Delete in order to respect foreign key constraints
            print("\n🗑️  Deleting related data...")
            
            # 1. Delete play records (user attempts)
            cursor.execute("DELETE FROM play")
            print(f"   - Deleted {cursor.rowcount} play records")
            
            # 2. Delete cluster associations
            cursor.execute("DELETE FROM cluster_roleplay")
            print(f"   - Deleted {cursor.rowcount} cluster-roleplay associations")
            
            # 3. Delete roleplay configs
            cursor.execute("DELETE FROM roleplay_config")
            print(f"   - Deleted {cursor.rowcount} roleplay configs")
            
            # 4. Delete roleplay overrides
            cursor.execute("DELETE FROM roleplayoverride")
            print(f"   - Deleted {cursor.rowcount} roleplay overrides")
            
            # 5. Finally, delete all roleplays
            cursor.execute("DELETE FROM roleplay")
            print(f"   - Deleted {cursor.rowcount} roleplays")
            
            # Commit the transaction
            dbconn.commit()
            
            print(f"\n✅ Successfully deleted all {count} roleplays and their related data!")
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    clear_all_roleplays()
