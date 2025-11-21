"""
Create missing cluster tables in database
Run this script on PythonAnywhere or locally to add the missing tables
"""
import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

# Database configuration
host = os.getenv('DB_HOST', 'localhost')
user = os.getenv('DB_USER', 'root')
password = os.getenv('DB_PASSWORD')
database = os.getenv('DB_NAME', 'roleplay')

def create_cluster_tables():
    """Create all cluster-related tables"""
    try:
        # Connect to database
        conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database
        )
        cursor = conn.cursor()
        
        print(f"Connected to database: {database}")
        
        # Read SQL file
        sql_file = os.path.join(os.path.dirname(__file__), 'create_cluster_tables.sql')
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Split by semicolons and execute each statement
        statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip() and not stmt.strip().startswith('--')]
        
        for idx, statement in enumerate(statements, 1):
            if statement:
                try:
                    print(f"\n[{idx}/{len(statements)}] Executing:")
                    print(statement[:100] + "..." if len(statement) > 100 else statement)
                    cursor.execute(statement)
                    conn.commit()
                    print("✓ Success")
                except mysql.connector.Error as e:
                    # If error is about column/table already existing, that's OK
                    if 'Duplicate column name' in str(e) or 'already exists' in str(e):
                        print(f"⚠ Already exists (skipping): {e}")
                    else:
                        print(f"✗ Error: {e}")
                        raise
        
        # Verify tables were created
        print("\n" + "="*60)
        print("Verifying tables...")
        cursor.execute("SHOW TABLES")
        tables = [table[0] for table in cursor.fetchall()]
        
        required_tables = ['roleplay_cluster', 'cluster_roleplay', 'user_cluster']
        for table in required_tables:
            if table in tables:
                print(f"✓ Table '{table}' exists")
                # Show table structure
                cursor.execute(f"DESCRIBE {table}")
                columns = cursor.fetchall()
                print(f"  Columns: {', '.join([col[0] for col in columns])}")
            else:
                print(f"✗ Table '{table}' NOT FOUND")
        
        # Check user table for is_admin column
        cursor.execute("DESCRIBE user")
        user_columns = [col[0] for col in cursor.fetchall()]
        if 'is_admin' in user_columns:
            print(f"✓ Column 'user.is_admin' exists")
        else:
            print(f"✗ Column 'user.is_admin' NOT FOUND")
        
        # Check roleplay table for new columns
        cursor.execute("DESCRIBE roleplay")
        roleplay_columns = [col[0] for col in cursor.fetchall()]
        for col in ['scenario_file_path', 'logo_path']:
            if col in roleplay_columns:
                print(f"✓ Column 'roleplay.{col}' exists")
            else:
                print(f"✗ Column 'roleplay.{col}' NOT FOUND")
        
        cursor.close()
        conn.close()
        
        print("\n" + "="*60)
        print("✓ All cluster tables created successfully!")
        print("\nYou can now:")
        print("1. Create clusters in the admin panel")
        print("2. Add roleplays to clusters")
        print("3. Assign clusters to users")
        print("4. Users will see their assigned roleplays")
        
    except Exception as e:
        print(f"\n✗ Error creating tables: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == '__main__':
    print("="*60)
    print("Creating Cluster Tables")
    print("="*60)
    create_cluster_tables()
