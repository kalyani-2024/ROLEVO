
import mysql.connector as ms
import os
from dotenv import load_dotenv

load_dotenv()

host = os.getenv('DB_HOST', 'localhost')
user = os.getenv('DB_USER', 'root')
password = os.getenv('DB_PASSWORD')
database = os.getenv('DB_NAME', 'roleplay')

try:
    conn = ms.connect(host=host, user=user, password=password, database=database)
    cur = conn.cursor()
    
    tables = ['roleplay_cluster', 'user_cluster', 'user']
    
    for table in tables:
        print(f"\n--- DESCRIBE {table} ---")
        try:
            cur.execute(f"DESCRIBE {table}")
            for row in cur.fetchall():
                print(row)
        except Exception as e:
            print(f"Error describing {table}: {e}")
            
    conn.close()
except Exception as e:
    print(e)
