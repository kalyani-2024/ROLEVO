"""
Migration script to add viewed_optimal column to play table.
This column tracks whether a user has viewed the optimal roleplay video.

Run this script once to add the column to your database.
"""
import mysql.connector
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def add_viewed_optimal_column():
    """Add viewed_optimal column to play table"""
    try:
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', ''),
            database=os.getenv('DB_NAME', 'rolevo')
        )
        cur = conn.cursor()
        
        # Check if column already exists
        cur.execute("""
            SELECT COUNT(*) 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'play' 
            AND COLUMN_NAME = 'viewed_optimal'
        """, (os.getenv('DB_NAME', 'rolevo'),))
        
        if cur.fetchone()[0] > 0:
            print("✅ Column 'viewed_optimal' already exists in play table")
        else:
            # Add the column
            cur.execute("""
                ALTER TABLE play 
                ADD COLUMN viewed_optimal BOOLEAN DEFAULT FALSE
            """)
            conn.commit()
            print("✅ Successfully added 'viewed_optimal' column to play table")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error adding column: {str(e)}")
        raise

if __name__ == "__main__":
    add_viewed_optimal_column()
