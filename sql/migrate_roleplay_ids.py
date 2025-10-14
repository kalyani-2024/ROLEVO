"""
Safe migration script to convert roleplay.id and all referencing columns to VARCHAR(100).

Usage (dry-run):
    python migrate_roleplay_ids.py

To apply changes:
    python migrate_roleplay_ids.py --apply

This script will:
 - connect to the MySQL database (defaults are in this file)
 - find all foreign keys that reference roleplay(id)
 - drop those foreign keys
 - alter referencing columns to VARCHAR(100)
 - alter roleplay.id to VARCHAR(100)
 - recreate the foreign keys with the original ON UPDATE/ON DELETE rules

IMPORTANT: ALWAYS BACKUP your database before running this script.
You can backup with mysqldump or any DB backup tool:

mysqldump -u root -p roleplay > roleplay_backup.sql

"""
import argparse
import mysql.connector
import getpass
import sys
import pprint


# Default connection settings (edit if needed)
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Kalkamal2005!',
    'database': 'roleplay',
}


def get_fk_constraints(cursor):
    """Return list of dicts describing foreign keys referencing roleplay(id)."""
    query = (
        "SELECT kcu.CONSTRAINT_NAME, kcu.TABLE_NAME, kcu.COLUMN_NAME, rc.UPDATE_RULE, rc.DELETE_RULE "
        "FROM information_schema.KEY_COLUMN_USAGE kcu "
        "JOIN information_schema.REFERENTIAL_CONSTRAINTS rc "
        "  ON kcu.CONSTRAINT_NAME = rc.CONSTRAINT_NAME AND kcu.CONSTRAINT_SCHEMA = rc.CONSTRAINT_SCHEMA "
        "WHERE kcu.REFERENCED_TABLE_NAME = 'roleplay' AND kcu.REFERENCED_COLUMN_NAME = 'id' "
        "  AND kcu.CONSTRAINT_SCHEMA = %s"
    )
    cursor.execute(query, (DB_CONFIG['database'],))
    rows = cursor.fetchall()
    fks = []
    for r in rows:
        fks.append({
            'constraint_name': r[0],
            'table_name': r[1],
            'column_name': r[2],
            'update_rule': r[3],
            'delete_rule': r[4],
        })
    return fks


def build_statements(fks):
    stmts = []
    # Drop FKs
    for fk in fks:
        stmts.append(("drop_fk", fk, f"ALTER TABLE `{fk['table_name']}` DROP FOREIGN KEY `{fk['constraint_name']}`;"))

    # Alter referencing columns to VARCHAR(100)
    for fk in fks:
        stmts.append(("alter_col", fk, f"ALTER TABLE `{fk['table_name']}` MODIFY COLUMN `{fk['column_name']}` VARCHAR(100) NOT NULL;"))

    # Alter roleplay.id
    stmts.append(("alter_roleplay", None, "ALTER TABLE `roleplay` MODIFY COLUMN `id` VARCHAR(100) NOT NULL;"))

    # Recreate FKs
    for fk in fks:
        add_fk = (
            f"ALTER TABLE `{fk['table_name']}` ADD CONSTRAINT `{fk['constraint_name']}` FOREIGN KEY (`{fk['column_name']}`) "
            f"REFERENCES `roleplay`(`id`) ON UPDATE {fk['update_rule']} ON DELETE {fk['delete_rule']};"
        )
        stmts.append(("add_fk", fk, add_fk))

    return stmts


def run(cursor, stmts, apply=False):
    for kind, fk, s in stmts:
        print('--', kind, '-', fk['table_name'] + 
              ('.' + fk['column_name'] if 'column_name' in fk else '' ) if fk else '')
        print(s)
        if apply:
            cursor.execute(s)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true', help='Apply the migration (default: dry-run)')
    parser.add_argument('--host', default=DB_CONFIG['host'])
    parser.add_argument('--user', default=DB_CONFIG['user'])
    parser.add_argument('--database', default=DB_CONFIG['database'])
    args = parser.parse_args()

    password = DB_CONFIG.get('password')
    if not password:
        password = getpass.getpass('MySQL password: ')

    DB_CONFIG['host'] = args.host
    DB_CONFIG['user'] = args.user
    DB_CONFIG['database'] = args.database
    DB_CONFIG['password'] = password

    print('Connecting to', DB_CONFIG['host'], 'as', DB_CONFIG['user'], 'db:', DB_CONFIG['database'])
    conn = mysql.connector.connect(host=DB_CONFIG['host'], user=DB_CONFIG['user'], password=DB_CONFIG['password'], database=DB_CONFIG['database'])
    cursor = conn.cursor()

    fks = get_fk_constraints(cursor)
    if not fks:
        print('No foreign keys found referencing roleplay(id). There may still be columns to alter.')
    else:
        print('Found foreign keys:')
        pprint.pprint(fks)

    stmts = build_statements(fks)

    if args.apply:
        confirm = input('This will modify the database schema. Have you backed up the DB? Type YES to continue: ')
        if confirm != 'YES':
            print('Aborting.')
            sys.exit(1)

        try:
            print('Disabling foreign key checks...')
            cursor.execute('SET FOREIGN_KEY_CHECKS=0;')
            run(cursor, stmts, apply=True)
            cursor.execute('SET FOREIGN_KEY_CHECKS=1;')
            conn.commit()
            print('Migration applied successfully.')
        except Exception as e:
            print('Error during migration:', e)
            conn.rollback()
            print('Rolled back. Please inspect the database and logs.')
    else:
        print('\nDRY RUN - SQL statements that would be executed:')
        run(cursor, stmts, apply=False)
        print('\nRun with --apply to execute these statements. BACKUP BEFORE RUNNING.')


if __name__ == '__main__':
    main()
