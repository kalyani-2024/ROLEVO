"""
Script to create missing roleplay_config entries for existing roleplays.

This fixes the issue where roleplays created before the config system was added
don't have entries in the roleplay_config table, causing 16PF and other config
options to not work.

Also adds missing 16PF columns if they don't exist.

Usage:
    python sql/fix_missing_roleplay_config.py
"""

import os
import sys
from dotenv import load_dotenv

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

import mysql.connector


def add_missing_16pf_columns(cursor):
    """Add 16PF columns to roleplay_config if they don't exist."""
    
    print("\n📋 Checking for missing columns...")
    
    # Get existing columns
    cursor.execute("DESCRIBE roleplay_config")
    existing_columns = [row['Field'] for row in cursor.fetchall()]
    print(f"   Existing columns: {existing_columns}")
    
    # Define columns that need to exist (in order of dependency)
    # Format: (column_name, column_definition, after_column or None)
    columns_to_add = [
        ("difficulty_level", "VARCHAR(20) DEFAULT 'easy'", "voice_assessment_enabled"),
        ("enable_16pf_analysis", "TINYINT(1) DEFAULT 0", "difficulty_level"),
        ("pf16_analysis_source", "VARCHAR(50) DEFAULT 'none'", "enable_16pf_analysis"),
        ("pf16_user_age_required", "TINYINT(1) DEFAULT 1", "pf16_analysis_source"),
        ("pf16_user_gender_required", "TINYINT(1) DEFAULT 1", "pf16_user_age_required"),
        ("pf16_default_age", "INT DEFAULT 30", "pf16_user_gender_required"),
        ("pf16_send_audio_for_analysis", "TINYINT(1) DEFAULT 1", "pf16_default_age"),
    ]
    
    added_columns = []
    for col_name, col_def, after_col in columns_to_add:
        if col_name not in existing_columns:
            try:
                # Check if the "after" column exists, if not just append
                if after_col and after_col in existing_columns:
                    sql = f"ALTER TABLE roleplay_config ADD COLUMN {col_name} {col_def} AFTER {after_col}"
                else:
                    sql = f"ALTER TABLE roleplay_config ADD COLUMN {col_name} {col_def}"
                cursor.execute(sql)
                added_columns.append(col_name)
                existing_columns.append(col_name)  # Update for next iteration
                print(f"   ✅ Added column: {col_name}")
            except mysql.connector.Error as e:
                if e.errno == 1060:  # Duplicate column
                    print(f"   ⏭️ Column already exists: {col_name}")
                else:
                    print(f"   ❌ Error adding {col_name}: {e}")
        else:
            print(f"   ⏭️ Column already exists: {col_name}")
    
    if added_columns:
        print(f"\n✅ Added {len(added_columns)} new column(s) to roleplay_config")
    else:
        print("\n✅ All 16PF columns already exist")
    
    return True


def fix_missing_roleplay_configs():
    """Create roleplay_config entries for any roleplays that don't have one."""
    
    print("=" * 60)
    print("Fix Missing Roleplay Config Entries")
    print("=" * 60)
    
    try:
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME', 'roleplay')
        )
        cursor = conn.cursor(dictionary=True)
        
        # First, add any missing 16PF columns
        add_missing_16pf_columns(cursor)
        conn.commit()
        
        # Find all roleplays without a config entry
        cursor.execute("""
            SELECT r.id, r.name 
            FROM roleplay r
            LEFT JOIN roleplay_config rc ON r.id = rc.roleplay_id
            WHERE rc.id IS NULL
        """)
        
        missing_configs = cursor.fetchall()
        
        if not missing_configs:
            print("\n✅ All roleplays have config entries. No action needed.")
            return True
        
        print(f"\n⚠️ Found {len(missing_configs)} roleplay(s) without config entries:")
        for rp in missing_configs:
            print(f"   - Roleplay ID: {rp['id']}, Name: {rp['name']}")
        
        print("\nCreating default config entries...")
        
        # Create default config for each missing roleplay
        insert_query = """
            INSERT INTO roleplay_config (
                roleplay_id, input_type, audio_rerecord_attempts, available_languages,
                max_interaction_time, max_total_time, repeat_attempts_allowed,
                score_type, show_ideal_video, ideal_video_path, voice_assessment_enabled,
                difficulty_level, enable_16pf_analysis, pf16_analysis_source,
                pf16_user_age_required, pf16_user_gender_required, pf16_default_age,
                pf16_send_audio_for_analysis
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        for rp in missing_configs:
            cursor.execute(insert_query, (
                rp['id'],           # roleplay_id
                'both',             # input_type - allow both text and audio
                3,                  # audio_rerecord_attempts
                '["English"]',      # available_languages - JSON string
                300,                # max_interaction_time (5 min)
                1800,               # max_total_time (30 min)
                1,                  # repeat_attempts_allowed
                'last',             # score_type
                False,              # show_ideal_video
                '',                 # ideal_video_path
                False,              # voice_assessment_enabled
                'easy',             # difficulty_level
                False,              # enable_16pf_analysis - disabled by default
                'none',             # pf16_analysis_source
                True,               # pf16_user_age_required
                True,               # pf16_user_gender_required
                30,                 # pf16_default_age
                True                # pf16_send_audio_for_analysis
            ))
            print(f"   ✅ Created config for roleplay ID: {rp['id']}")
        
        conn.commit()
        print(f"\n✅ Successfully created {len(missing_configs)} config entries.")
        print("\n📝 NOTE: To enable 16PF analysis, go to Admin Panel -> Edit Roleplay -> Enable 16PF Voice Analysis -> Save")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    fix_missing_roleplay_configs()
