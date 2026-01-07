import mysql.connector
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

conn = mysql.connector.connect(
    host=os.getenv('DB_HOST', 'localhost'),
    user=os.getenv('DB_USER', 'root'),
    password=os.getenv('DB_PASSWORD'),
    database=os.getenv('DB_NAME', 'roleplay')
)

cur = conn.cursor()
cur.execute('SELECT id, name, competency_file_path, scenario_file_path, logo_path FROM roleplay ORDER BY name')
rows = cur.fetchall()

print("=== CHECKING FOR DATETIME VALUES IN FILE PATH COLUMNS ===\n")

datetime_issues = []

for row in rows:
    roleplay_id = row[0]
    name = row[1]
    comp = row[2]
    scenario = row[3]
    logo = row[4]
    
    has_issue = False
    issues = []
    
    if isinstance(comp, datetime):
        has_issue = True
        issues.append(f"competency_file_path is datetime: {comp}")
    
    if isinstance(scenario, datetime):
        has_issue = True
        issues.append(f"scenario_file_path is datetime: {scenario}")
    
    if isinstance(logo, datetime):
        has_issue = True
        issues.append(f"logo_path is datetime: {logo}")
    
    if has_issue:
        print(f"❌ ID: {roleplay_id}, Name: {name}")
        for issue in issues:
            print(f"   {issue}")
        print()
        datetime_issues.append(roleplay_id)
    else:
        print(f"✅ ID: {roleplay_id}, Name: {name} - All file paths are correct type")

print(f"\n=== SUMMARY ===")
print(f"Total roleplays with datetime issues: {len(datetime_issues)}")
if datetime_issues:
    print(f"IDs: {', '.join(datetime_issues)}")
    print("\nFixing these records...")
    
    for roleplay_id in datetime_issues:
        cur.execute("""
            UPDATE roleplay 
            SET competency_file_path = CASE 
                WHEN competency_file_path IS NOT NULL AND competency_file_path REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2}' THEN NULL
                ELSE competency_file_path 
            END,
            scenario_file_path = CASE 
                WHEN scenario_file_path IS NOT NULL AND scenario_file_path REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2}' THEN NULL
                ELSE scenario_file_path 
            END,
            logo_path = CASE 
                WHEN logo_path IS NOT NULL AND logo_path REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2}' THEN NULL
                ELSE logo_path 
            END
            WHERE id = %s
        """, (roleplay_id,))
    
    conn.commit()
    print(f"✅ Fixed {len(datetime_issues)} roleplays - set datetime values to NULL")

cur.close()
conn.close()
