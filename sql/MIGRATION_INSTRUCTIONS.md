Migration instructions — converting roleplay.id to VARCHAR(100)

Overview

The repository schema was changed so `roleplay.id` is a VARCHAR(100) primary key (previously integer AUTO_INCREMENT).
If your live MySQL database was already created with the old schema, you'll need to migrate it before using alphanumeric roleplay IDs (e.g., "2_rolex").

This folder includes a helper script `migrate_roleplay_ids.py` that prints and optionally executes the migration SQL.

Important: BACK UP your database before running any migration. The script will prompt for explicit confirmation.

Quick backup command (run from PowerShell or bash):

mysqldump -u root -p roleplay > roleplay_backup.sql

Dry-run

1. From your project root run (dry-run):

python .\sql\migrate_roleplay_ids.py

2. Inspect the SQL statements printed. These include dropping FKs, altering columns to VARCHAR(100), and recreating FKs.

Apply migration

1. Ensure you have a backup (see above).
2. Run:

python .\sql\migrate_roleplay_ids.py --apply

3. Type YES when prompted to proceed.

Notes & caveats

- The script disables foreign key checks temporarily while applying statements. It attempts to restore them afterward.
- If your database uses different constraint names, the script reads actual constraint names from information_schema and recreates them.
- This script is intended for moderate-sized DBs. For very large DBs, test the migration on a copy first.
- If you have application code or external tools depending on numeric ids, update them accordingly.

If you want, I can:
- Generate a SQL-only migration file instead of a Python script.
- Help run the migration (if you paste the dry-run output or run the script and paste the results here).
- Add a post-migration verification script to check referential integrity and that sample alphanumeric ids work.
