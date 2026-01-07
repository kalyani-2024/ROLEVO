"""
Import MySQL database dump
"""
import mysql.connector as ms
import os
from dotenv import load_dotenv

load_dotenv()

host = os.getenv('DB_HOST', 'localhost')
user = os.getenv('DB_USERNAME', 'root')
password = os.getenv('DB_PASSWORD', '')
database = os.getenv('DB_NAME', 'roleplay')

# Path to your SQL dump file
sql_file = r'C:\Users\lenovo\OneDrive\Documents\dumps\rolevo.sql'

try:
    print(f"Connecting to MySQL server at {host}...")
    conn = ms.connect(
        host=host,
        user=user,
        password=password
    )
    cursor = conn.cursor()
    
    # Create database if it doesn't exist
    print(f"Creating database '{database}' if it doesn't exist...")
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database} CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci")
    cursor.execute(f"USE {database}")
    
    # Disable foreign key checks
    print("Disabling foreign key checks...")
    cursor.execute("SET FOREIGN_KEY_CHECKS=0")
    
    # Read and execute SQL file
    print(f"Reading SQL file: {sql_file}")
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # Split by semicolons and execute each statement
    print("Executing SQL statements...")
    statements = sql_content.split(';')
    
    for i, statement in enumerate(statements):
        statement = statement.strip()
        if statement and not statement.startswith('--') and not statement.startswith('/*'):
            try:
                cursor.execute(statement)
            except Exception as e:
                # Skip comments and empty statements
                if 'empty query' not in str(e).lower():
                    print(f"Warning on statement {i}: {str(e)[:100]}")
    
    # Re-enable foreign key checks
    print("Re-enabling foreign key checks...")
    cursor.execute("SET FOREIGN_KEY_CHECKS=1")
    
    # Commit changes
    conn.commit()
    print("\n✅ Database import completed successfully!")
    
    # Show tables
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    print(f"\n📊 Tables created: {len(tables)}")
    for table in tables:
        print(f"   - {table[0]}")
    
except ms.Error as err:
    print(f"❌ MySQL Error: {err}")
except FileNotFoundError:
    print(f"❌ SQL file not found: {sql_file}")
except Exception as e:
    print(f"❌ Error: {e}")
finally:
    if 'conn' in locals() and conn.is_connected():
        cursor.close()
        conn.close()
        print("\nDatabase connection closed.")
