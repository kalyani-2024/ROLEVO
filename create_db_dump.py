import os
import subprocess
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

host = os.getenv('DB_HOST', 'localhost')
user = os.getenv('DB_USER', 'root')
password = os.getenv('DB_PASSWORD', '')
database = os.getenv('DB_NAME', 'roleplay')

# Path to mysqldump (found via previous search)
MYSQLDUMP_PATH = r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe"

output_file = "rolevo_db_dump.sql"

print(f"Generating database dump for '{database}'...")

# Prepare environment with password
env = os.environ.copy()
if password:
    env['MYSQL_PWD'] = password

# Construct command
# --routines: dump stored procedures/functions
# --triggers: dump triggers
# --single-transaction: consistent snapshot (good for InnoDB)
cmd = [
    MYSQLDUMP_PATH,
    "-h", host,
    "-u", user,
    "--routines",
    "--triggers",
    "--single-transaction",
    "--result-file=" + output_file,
    database
]

try:
    subprocess.run(cmd, env=env, check=True)
    print(f"SUCCESS: Database dump created at '{os.path.abspath(output_file)}'")
    print("You can upload this file to your GoDaddy MySQL server (using phpMyAdmin import feature).")
except subprocess.CalledProcessError as e:
    print(f"ERROR: Failed to create dump. Return code: {e.returncode}")
except FileNotFoundError:
    print(f"ERROR: Could not find mysqldump at {MYSQLDUMP_PATH}")
except Exception as e:
    print(f"An error occurred: {str(e)}")
