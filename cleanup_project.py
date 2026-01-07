"""
Project Cleanup Script
Moves unnecessary files to _backup_to_delete/ folder for review
Run this script, review the moved files, then delete _backup_to_delete/ if satisfied
"""

import os
import shutil
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent
BACKUP_DIR = BASE_DIR / "_backup_to_delete"

# Files to move to backup
FILES_TO_REMOVE = [
    "tempp.py",
    "diagnose_reports.py",
    "test_report_system.py",
    "import_database.py",
    "temp_broken_image_test.xlsx",
    "basereport.html",
    "admin_button_examples.html",
    "sample.json",
    "packages.txt",
    "realreqs.txt",
    "mysql_creation.txt",
]

# Documentation files (optional - uncomment to remove)
DOC_FILES = [
    "IMPLEMENTATION_SUMMARY.md",
    "QUICK_START_REPORTS.md",
    "REPORT_SYSTEM_README.md",
    "EMAIL_SETUP.txt",
]

# SQL migration scripts to keep only the essential one
SQL_FILES_TO_REMOVE = [
    "sql/add_difficulty_level.py",
    "sql/add_is_admin_column.py",
    "sql/add_scenario_and_logo_columns.py",
    "sql/alter_roleplay_id_autoincrement.py",
    "sql/create_default_user.py",
    "sql/reset_admin_password.py",
    "sql/reset_password_bcrypt.py",
    "sql/check_tables.py",
    "sql/update_schema.py",
    "sql/migrate_roleplay_ids.py",
    "sql/initialization.py",  # Keep enhanced_initialization.py instead
    "sql/check_roleplay_schema.sql",
    "sql/create_cluster_tables.sql",
    "sql/create_cluster_tables_final.sql",
    "sql/create_cluster_tables_script.py",
    "sql/create_cluster_tables_simple.sql",
    "sql/create_cluster_tables_v2.sql",
]

# Folders to remove
FOLDERS_TO_REMOVE = [
    "app/temp",
    "uploads",
    "sql/venv",
]

def move_to_backup(file_path, reason=""):
    """Move file to backup folder"""
    try:
        if not file_path.exists():
            print(f"⏭️  SKIP: {file_path} (doesn't exist)")
            return
        
        # Create backup directory structure
        relative_path = file_path.relative_to(BASE_DIR)
        backup_path = BACKUP_DIR / relative_path
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Move file
        shutil.move(str(file_path), str(backup_path))
        print(f"✅ MOVED: {relative_path} {reason}")
        
    except Exception as e:
        print(f"❌ ERROR moving {file_path}: {e}")

def main():
    print("=" * 70)
    print("ROLEVO PROJECT CLEANUP")
    print("=" * 70)
    print(f"Backup folder: {BACKUP_DIR}")
    print()
    
    # Create backup directory
    BACKUP_DIR.mkdir(exist_ok=True)
    
    # Move individual files
    print("\n📄 Moving unnecessary files...")
    print("-" * 70)
    for filename in FILES_TO_REMOVE:
        file_path = BASE_DIR / filename
        move_to_backup(file_path, "(test/temp file)")
    
    # Move SQL migration scripts
    print("\n🗄️  Moving one-time SQL migration scripts...")
    print("-" * 70)
    for filename in SQL_FILES_TO_REMOVE:
        file_path = BASE_DIR / filename
        move_to_backup(file_path, "(one-time migration)")
    
    # Move folders
    print("\n📁 Moving empty/unnecessary folders...")
    print("-" * 70)
    for folder in FOLDERS_TO_REMOVE:
        folder_path = BASE_DIR / folder
        if folder_path.exists():
            move_to_backup(folder_path, "(empty/unused folder)")
    
    # Optional: Move documentation files
    # Uncomment the next block if you want to remove documentation too
    # print("\n📝 Moving documentation files...")
    # print("-" * 70)
    # for filename in DOC_FILES:
    #     file_path = BASE_DIR / filename
    #     move_to_backup(file_path, "(documentation)")
    
    print("\n" + "=" * 70)
    print("✅ CLEANUP COMPLETE!")
    print("=" * 70)
    print(f"\nAll files moved to: {BACKUP_DIR}")
    print("\n📋 NEXT STEPS:")
    print("1. Review the files in _backup_to_delete/")
    print("2. Test your application to ensure everything works")
    print("3. If satisfied, delete the entire _backup_to_delete/ folder")
    print("4. If something broke, move files back from _backup_to_delete/")
    print("\n⚠️  NOTE: The old excel_validator.py will be handled separately")
    
if __name__ == "__main__":
    main()
