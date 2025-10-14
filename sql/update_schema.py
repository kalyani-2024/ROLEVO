import mysql.connector as ms

# Connect to database
conn = ms.connect(host='localhost', user='root', password="Kalkamal2005!", database='roleplay')
print("Connected to database successfully")

cur = conn.cursor()

# Check and create roleplay_config table if it doesn't exist
try:
    cur.execute('''
    CREATE TABLE IF NOT EXISTS roleplay_config (
        id INTEGER PRIMARY KEY AUTO_INCREMENT,
        roleplay_id INTEGER NOT NULL,
        input_type ENUM('audio', 'text') DEFAULT 'text',
        audio_rerecord_attempts INTEGER DEFAULT 3,
        available_languages JSON,
        max_interaction_time INTEGER DEFAULT 300,
        max_total_time INTEGER DEFAULT 1800,
        repeat_attempts_allowed INTEGER DEFAULT 1,
        score_type ENUM('best', 'last') DEFAULT 'last',
        show_ideal_video BOOLEAN DEFAULT FALSE,
        ideal_video_path VARCHAR(500),
        voice_assessment_enabled BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY(roleplay_id) REFERENCES roleplay(id) ON DELETE CASCADE
    )
    ''')
    print("roleplay_config table created successfully")
except Exception as e:
    print(f"roleplay_config table already exists or error: {e}")

# Check and create roleplay_cluster table if it doesn't exist
try:
    cur.execute('''
    CREATE TABLE IF NOT EXISTS roleplay_cluster (
        id INTEGER PRIMARY KEY AUTO_INCREMENT,
        name VARCHAR(1000) NOT NULL,
        cluster_id VARCHAR(100) NOT NULL UNIQUE,
        type ENUM('assessment', 'training') NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    )
    ''')
    print("roleplay_cluster table created successfully")
except Exception as e:
    print(f"roleplay_cluster table already exists or error: {e}")

# Check and create cluster_roleplay table if it doesn't exist
try:
    cur.execute('''
    CREATE TABLE IF NOT EXISTS cluster_roleplay (
        cluster_id INTEGER NOT NULL,
        roleplay_id INTEGER NOT NULL,
        order_sequence INTEGER DEFAULT 1,
        PRIMARY KEY(cluster_id, roleplay_id),
        FOREIGN KEY(cluster_id) REFERENCES roleplay_cluster(id) ON DELETE CASCADE,
        FOREIGN KEY(roleplay_id) REFERENCES roleplay(id) ON DELETE CASCADE
    )
    ''')
    print("cluster_roleplay table created successfully")
except Exception as e:
    print(f"cluster_roleplay table already exists or error: {e}")

# Add new columns to existing play table if they don't exist
try:
    cur.execute("ALTER TABLE play ADD COLUMN end_time DATETIME NULL")
    print("Added end_time column to play table")
except Exception as e:
    print(f"end_time column already exists or error: {e}")

try:
    cur.execute("ALTER TABLE play ADD COLUMN cluster_id INTEGER NULL")
    print("Added cluster_id column to play table")
except Exception as e:
    print(f"cluster_id column already exists or error: {e}")

try:
    cur.execute("ALTER TABLE play ADD COLUMN attempt_number INTEGER DEFAULT 1")
    print("Added attempt_number column to play table")
except Exception as e:
    print(f"attempt_number column already exists or error: {e}")

try:
    cur.execute("ALTER TABLE play ADD COLUMN total_time_spent INTEGER DEFAULT 0")
    print("Added total_time_spent column to play table")
except Exception as e:
    print(f"total_time_spent column already exists or error: {e}")

try:
    cur.execute("ALTER TABLE play ADD COLUMN status ENUM('ongoing', 'completed', 'abandoned') DEFAULT 'ongoing'")
    print("Added status column to play table")
except Exception as e:
    print(f"status column already exists or error: {e}")

# Add new columns to chathistory table if they don't exist
try:
    cur.execute("ALTER TABLE chathistory ADD COLUMN interaction_time INTEGER DEFAULT 0")
    print("Added interaction_time column to chathistory table")
except Exception as e:
    print(f"interaction_time column already exists or error: {e}")

try:
    cur.execute("ALTER TABLE chathistory ADD COLUMN audio_file_path VARCHAR(500)")
    print("Added audio_file_path column to chathistory table")
except Exception as e:
    print(f"audio_file_path column already exists or error: {e}")

try:
    cur.execute("ALTER TABLE chathistory ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    print("Added created_at column to chathistory table")
except Exception as e:
    print(f"created_at column already exists or error: {e}")

# Add created_at column to scoremaster table if it doesn't exist
try:
    cur.execute("ALTER TABLE scoremaster ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    print("Added created_at column to scoremaster table")
except Exception as e:
    print(f"created_at column already exists or error: {e}")

# Add id column to scorebreakdown table if it doesn't exist
try:
    cur.execute("ALTER TABLE scorebreakdown ADD COLUMN id INTEGER PRIMARY KEY AUTO_INCREMENT FIRST")
    print("Added id column to scorebreakdown table")
except Exception as e:
    print(f"id column already exists or error: {e}")

# Insert default configuration for existing roleplays that don't have config
try:
    cur.execute("""
    INSERT INTO roleplay_config (
        roleplay_id, 
        input_type, 
        audio_rerecord_attempts, 
        available_languages, 
        max_interaction_time, 
        max_total_time, 
        repeat_attempts_allowed, 
        score_type, 
        show_ideal_video, 
        voice_assessment_enabled
    )
    SELECT 
        r.id,
        'text',
        3,
        '["English", "Hindi"]',
        300,
        1800,
        1,
        'last',
        FALSE,
        FALSE
    FROM roleplay r
    LEFT JOIN roleplay_config rc ON r.id = rc.roleplay_id
    WHERE rc.roleplay_id IS NULL
    """)
    print("Added default configurations for existing roleplays")
except Exception as e:
    print(f"Error adding default configurations: {e}")

print("Database schema updated successfully with new configuration options")
conn.commit()
conn.close()