import mysql.connector

try:
    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='Kalkamal2005!',
        database='roleplay'
    )
    cursor = conn.cursor()
    
    print("Creating missing tables...")
    
    # Create play table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS play (
        id INTEGER PRIMARY KEY AUTO_INCREMENT,
        start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
        end_time DATETIME NULL,
        user_id INTEGER NOT NULL,
        roleplay_id VARCHAR(100) NOT NULL,
        cluster_id INTEGER NULL,
        attempt_number INTEGER DEFAULT 1,
        total_time_spent INTEGER DEFAULT 0,
        status ENUM('ongoing', 'completed', 'abandoned') DEFAULT 'ongoing',
        FOREIGN KEY(user_id) REFERENCES user(id),
        FOREIGN KEY(roleplay_id) REFERENCES roleplay(id),
        FOREIGN KEY(cluster_id) REFERENCES roleplay_cluster(id)
    )
    ''')
    print("Created play table")
    
    # Create chathistory table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS chathistory (
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
    print("Created chathistory table")
    
    # Create scoremaster table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS scoremaster (
        id INTEGER PRIMARY KEY AUTO_INCREMENT,
        chathistory_id INTEGER NOT NULL,
        overall_score INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(chathistory_id) REFERENCES chathistory(id) ON DELETE CASCADE
    )
    ''')
    print("Created scoremaster table")
    
    # Create scorebreakdown table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS scorebreakdown (
        id INTEGER PRIMARY KEY AUTO_INCREMENT,
        scoremaster_id INTEGER NOT NULL,
        score_name VARCHAR(255) NOT NULL,
        score INTEGER NOT NULL,
        FOREIGN KEY(scoremaster_id) REFERENCES scoremaster(id) ON DELETE CASCADE
    )
    ''')
    print("Created scorebreakdown table")
    
    # Create roleplayoverride table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS roleplayoverride (
        roleplay_id VARCHAR(100) NOT NULL,
        user_id INTEGER NOT NULL,
        PRIMARY KEY(roleplay_id, user_id),
        FOREIGN KEY(roleplay_id) REFERENCES roleplay(id) ON DELETE CASCADE,
        FOREIGN KEY(user_id) REFERENCES user(id) ON DELETE CASCADE
    )
    ''')
    print("Created roleplayoverride table")
    
    conn.commit()
    print("All missing tables created successfully!")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()