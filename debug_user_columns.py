
import mysql.connector as ms
import os
from dotenv import load_dotenv

load_dotenv()

host = os.getenv('DB_HOST', 'localhost')
user = os.getenv('DB_USER', 'root')
password = os.getenv('DB_PASSWORD')
database = os.getenv('DB_NAME', 'roleplay')

log = open('debug_user_schema_log.txt', 'w')

try:
    conn = ms.connect(host=host, user=user, password=password, database=database)
    cur = conn.cursor()
    
    log.write("--- USER TABLE COLUMNS ---\n")
    cur.execute("SHOW COLUMNS FROM user")
    for row in cur.fetchall():
        log.write(str(row) + "\n")
        
    log.write("\n--- TESTING QUERY ---\n")
    try:
        cur.execute("SELECT id, email, name, created_at FROM user LIMIT 1")
        log.write("Query 'SELECT id, email, name, created_at' SUCCESS\n")
    except Exception as qe:
        log.write(f"Query FAILED: {qe}\n")
        
        # Try without name
        try:
            cur.execute("SELECT id, email, created_at FROM user LIMIT 1")
            log.write("Query 'SELECT id, email, created_at' SUCCESS\n")
        except Exception as qe2:
             log.write(f"Query 2 FAILED: {qe2}\n")

    conn.close()
except Exception as e:
    log.write(f"Global Error: {e}\n")

log.close()
