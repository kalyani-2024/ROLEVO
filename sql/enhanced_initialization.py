import mysql.connector as ms

# Connect to database
conn = ms.connect(host='localhost', user='root', password="Kalkamal2005!", database='roleplay')
print("Connected to database successfully")

cur = conn.cursor()

# Drop existing tables to recreate with new schema
drop_queries = [
    'DROP TABLE IF EXISTS cluster_roleplay',
    'DROP TABLE IF EXISTS roleplay_cluster', 
    'DROP TABLE IF EXISTS roleplay_config',
    'DROP TABLE IF EXISTS scorebreakdown',
    'DROP TABLE IF EXISTS scoremaster',
    'DROP TABLE IF EXISTS chathistory',
    'DROP TABLE IF EXISTS play',
    'DROP TABLE IF EXISTS roleplayoverride',
    'DROP TABLE IF EXISTS roleplay',
    'DROP TABLE IF EXISTS user'
]

for query in drop_queries:
    try:
        cur.execute(query)
    except:
        pass

# Create user table
cur.execute('''
CREATE TABLE user (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    email VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(500) NOT NULL
)
''')

# Create enhanced roleplay table
cur.execute('''
CREATE TABLE roleplay (
    id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(1000) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    image_file_path VARCHAR(500) NOT NULL,
    scenario VARCHAR(2000) NOT NULL,
    person_name VARCHAR(1000) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
)
''')

# Create roleplay configuration table for additional settings
cur.execute('''
CREATE TABLE roleplay_config (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    roleplay_id VARCHAR(100) NOT NULL,
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

# Create cluster table
cur.execute('''
CREATE TABLE roleplay_cluster (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(1000) NOT NULL,
    cluster_id VARCHAR(100) NOT NULL UNIQUE,
    type ENUM('assessment', 'training') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
)
''')

# Create cluster-roleplay mapping table
cur.execute('''
CREATE TABLE cluster_roleplay (
    cluster_id INTEGER NOT NULL,
    roleplay_id VARCHAR(100) NOT NULL,
    order_sequence INTEGER DEFAULT 1,
    PRIMARY KEY(cluster_id, roleplay_id),
    FOREIGN KEY(cluster_id) REFERENCES roleplay_cluster(id) ON DELETE CASCADE,
    FOREIGN KEY(roleplay_id) REFERENCES roleplay(id) ON DELETE CASCADE
)
''')

# Create play table (updated)
cur.execute('''
CREATE TABLE play (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    end_time DATETIME NULL,
    user_id INTEGER NOT NULL,
    roleplay_id INTEGER NOT NULL,
    cluster_id INTEGER NULL,
    attempt_number INTEGER DEFAULT 1,
    total_time_spent INTEGER DEFAULT 0,
    status ENUM('ongoing', 'completed', 'abandoned') DEFAULT 'ongoing',
    FOREIGN KEY(user_id) REFERENCES user(id),
    FOREIGN KEY(roleplay_id) REFERENCES roleplay(id),
    FOREIGN KEY(cluster_id) REFERENCES roleplay_cluster(id)
)
''')

# Create chathistory table (updated)
cur.execute('''
CREATE TABLE chathistory (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    play_id INTEGER NOT NULL,
    user_text VARCHAR(2500),
    response_text VARCHAR(2500),
    interaction_time INTEGER DEFAULT 0,
    audio_file_path VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(play_id) REFERENCES play(id) ON DELETE CASCADE
)
''')

# Create scoremaster table
cur.execute('''
CREATE TABLE scoremaster (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    chathistory_id INTEGER NOT NULL,
    overall_score INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(chathistory_id) REFERENCES chathistory(id) ON DELETE CASCADE
)
''')

# Create scorebreakdown table
cur.execute('''
CREATE TABLE scorebreakdown (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    scoremaster_id INTEGER NOT NULL,
    score_name VARCHAR(255) NOT NULL,
    score INTEGER NOT NULL,
    FOREIGN KEY(scoremaster_id) REFERENCES scoremaster(id) ON DELETE CASCADE
)
''')

# Create roleplayoverride table
cur.execute('''
CREATE TABLE roleplayoverride (
    roleplay_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    PRIMARY KEY(roleplay_id, user_id),
    FOREIGN KEY(roleplay_id) REFERENCES roleplay(id) ON DELETE CASCADE,
    FOREIGN KEY(user_id) REFERENCES user(id) ON DELETE CASCADE
)
''')

# Insert sample data
cur.execute('''
INSERT INTO roleplay (id, name, file_path, image_file_path, scenario, person_name) 
VALUES ('1', 'Credit Roleplay', 'data/Roleplay 1.xls', 'data/images/Roleplay 1.xls', 'Credit discussion roleplay scenario', 'Mr. Sachin')
''')

roleplay_id = cur.lastrowid

# Insert default configuration for the sample roleplay
cur.execute('''
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
) VALUES (
    %s, 
    'text', 
    3, 
    '["English", "Hindi"]', 
    300, 
    1800, 
    1, 
    'last', 
    FALSE, 
    FALSE
)
''', (roleplay_id,))

print("Database schema updated successfully with new configuration options")
conn.commit()
conn.close()