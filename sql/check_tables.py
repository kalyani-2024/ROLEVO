import mysql.connector

try:
    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='Kalkamal2005!',
        database='roleplay'
    )
    cursor = conn.cursor()
    
    print("Current tables:")
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    for table in tables:
        print(f"  {table[0]}")
    
    if tables:
        print("\nTable structures:")
        for table in tables:
            table_name = table[0]
            print(f"\n{table_name}:")
            cursor.execute(f"DESCRIBE {table_name}")
            columns = cursor.fetchall()
            for col in columns:
                print(f"  {col[0]} {col[1]} {col[2]} {col[3]} {col[4]} {col[5]}")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")