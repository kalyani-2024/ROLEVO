import os
import subprocess
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

host = os.getenv('DB_HOST', 'localhost')
user = os.getenv('DB_USER', 'root')
password = os.getenv('DB_PASSWORD', '')
database = os.getenv('DB_NAME', 'roleplay')

# Path to mysqldump
MYSQLDUMP_PATH = r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe"

output_file = "rolevo_schema_only.sql"

print(f"Generating SCHEMA-ONLY dump for '{database}' (Tables only, no data)...")

# Prepare environment with password
env = os.environ.copy()
if password:
    env['MYSQL_PWD'] = password

# Construct command
# --no-data: Do not dump table contents
cmd = [
    MYSQLDUMP_PATH,
    "-h", host,
    "-u", user,
    "--no-data", 
    "--routines",
    "--triggers",
    "--single-transaction",
    "--result-file=" + output_file,
    database
]

try:
    subprocess.run(cmd, env=env, check=True)
    print(f"SUCCESS: Schema dump created at '{os.path.abspath(output_file)}'")
    print("This file contains the commands to create all your tables without any data.")
except subprocess.CalledProcessError as e:
    print(f"ERROR: Failed to create dump. Return code: {e.returncode}")
except FileNotFoundError:
    print(f"ERROR: Could not find mysqldump at {MYSQLDUMP_PATH}")
except Exception as e:
    print(f"An error occurred: {str(e)}")
