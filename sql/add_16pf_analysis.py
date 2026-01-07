"""
Migration script to add 16PF voice analysis configuration to roleplay_config table.

This adds the following columns:
- enable_16pf_analysis: Boolean to enable/disable 16PF voice analysis
- pf16_analysis_source: Source of 16PF analysis ('persona360', 'third_party', 'none')
- pf16_user_age_required: Whether to require user age for analysis
- pf16_user_gender_required: Whether to require user gender for analysis

Run this script to update existing database:
    python sql/add_16pf_analysis.py
"""

import os
import sys
import MySQLdb as ms
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

host = os.getenv('DB_HOST', 'localhost')
user = os.getenv('DB_USER', 'root')
password = os.getenv('DB_PASSWORD')
database = os.getenv('DB_NAME', 'roleplay')


def migrate():
    """Add 16PF analysis columns to roleplay_config table."""
    print("=" * 60)
    print("16PF Voice Analysis Migration Script")
    print("=" * 60)
    
    try:
        conn = ms.connect(
            host=host,
            user=user,
            passwd=password,
            db=database
        )
        cur = conn.cursor()
        
        # Column definitions to add
        columns_to_add = [
            {
                "name": "enable_16pf_analysis",
                "definition": "BOOLEAN DEFAULT FALSE",
                "after": "difficulty_level"
            },
            {
                "name": "pf16_analysis_source",
                "definition": "ENUM('none', 'persona360', 'third_party') DEFAULT 'none'",
                "after": "enable_16pf_analysis"
            },
            {
                "name": "pf16_user_age_required",
                "definition": "BOOLEAN DEFAULT TRUE",
                "after": "pf16_analysis_source"
            },
            {
                "name": "pf16_user_gender_required", 
                "definition": "BOOLEAN DEFAULT TRUE",
                "after": "pf16_user_age_required"
            },
            {
                "name": "pf16_default_age",
                "definition": "INTEGER DEFAULT 30",
                "after": "pf16_user_gender_required"
            },
            {
                "name": "pf16_send_audio_for_analysis",
                "definition": "BOOLEAN DEFAULT TRUE",
                "after": "pf16_default_age"
            }
        ]
        
        for col in columns_to_add:
            try:
                # Check if column already exists
                cur.execute(f"SHOW COLUMNS FROM roleplay_config LIKE '{col['name']}'")
                if cur.fetchone():
                    print(f"✓ Column '{col['name']}' already exists - skipping")
                else:
                    # Add the column
                    sql = f"ALTER TABLE roleplay_config ADD COLUMN {col['name']} {col['definition']} AFTER {col['after']}"
                    cur.execute(sql)
                    conn.commit()
                    print(f"✓ Added column '{col['name']}' to roleplay_config")
            except Exception as e:
                print(f"✗ Error adding column '{col['name']}': {str(e)}")
        
        # Also create a table to store 16PF analysis results
        print("\nCreating 16PF analysis results table...")
        try:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS pf16_analysis_results (
                    id INTEGER PRIMARY KEY AUTO_INCREMENT,
                    play_id INTEGER NOT NULL,
                    user_id INTEGER,
                    roleplay_id VARCHAR(100),
                    audio_file_path VARCHAR(500),
                    analysis_source VARCHAR(50) DEFAULT 'persona360',
                    user_age INTEGER,
                    user_gender VARCHAR(20),
                    raw_response JSON,
                    personality_scores JSON,
                    composite_scores JSON,
                    overall_role_fit DECIMAL(5,2),
                    analysis_confidence DECIMAL(5,2),
                    status ENUM('pending', 'processing', 'completed', 'failed') DEFAULT 'pending',
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP NULL,
                    FOREIGN KEY(play_id) REFERENCES play(id) ON DELETE CASCADE
                )
            """)
            conn.commit()
            print("✓ Created pf16_analysis_results table")
        except Exception as e:
            if "already exists" in str(e).lower():
                print("✓ Table pf16_analysis_results already exists")
            else:
                print(f"✗ Error creating pf16_analysis_results table: {str(e)}")
        
        cur.close()
        conn.close()
        
        print("\n" + "=" * 60)
        print("Migration completed successfully!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n✗ Migration failed: {str(e)}")
        return False


if __name__ == "__main__":
    migrate()
