import mysql.connector as ms

conn = ms.connect(host='localhost', user='root', password="Kalkamal2005!", database='roleplay')
print("Opened database successfully")

cur = conn.cursor()
cur.execute('CREATE TABLE user (id INTEGER PRIMARY KEY, email VARCHAR(255) NOT NULL UNIQUE, password VARCHAR(500) NOT NULL)')

cur.execute('CREATE TABLE roleplay (id VARCHAR(100) PRIMARY KEY, name VARCHAR(1000) NOT NULL, file_path VARCHAR(500) NOT NULL, image_file_path VARCHAR(500) NOT NULL, scenario VARCHAR(1000) NOT NULL, person_name VARCHAR(1000) NOT NULL)')
cur.execute('CREATE TABLE play (id INTEGER PRIMARY KEY, start_time DATETIME DEFAULT CURRENT_TIMESTAMP, user_id INTEGER NOT NULL, roleplay_id INTEGER NOT NULL, FOREIGN KEY(user_id) REFERENCES user(id), FOREIGN KEY(roleplay_id) REFERENCES roleplay(id))')
cur.execute('CREATE TABLE chathistory (id INTEGER PRIMARY KEY, play_id INTEGER NOT NULL, user_text VARCHAR(2500), response_text VARCHAR(2500), FOREIGN KEY(play_id) REFERENCES play(id))')
cur.execute('CREATE TABLE scoremaster (id INTEGER PRIMARY KEY, chathistory_id INTEGER NOT NULL, overall_score INTEGER NOT NULL, FOREIGN KEY(chathistory_id) REFERENCES chathistory(id))')
cur.execute('CREATE TABLE scorebreakdown (scoremaster_id INTEGER NOT NULL, score_name VARCHAR(255) NOT NULL, score INTEGER NOT NULL, FOREIGN KEY(scoremaster_id) REFERENCES scoremaster(id))')
cur.execute('CREATE TABLE roleplayoverride (roleplay_id VARCHAR(100) NOT NULL, user_id INTEGER NOT NULL, FOREIGN KEY(roleplay_id) REFERENCES roleplay(id), FOREIGN KEY(user_id) REFERENCES user(id))')
cur.execute("INSERT INTO roleplay (name, file_path) VALUES ('Credit Roleplay', 'data/Roleplay 1.xls')")

query = "SELECT file_path FROM roleplay WHERE id = (?)"

roleplay_id = 1
cur.execute(query, (roleplay_id,))
result = cur.fetchone()
print(result)
print("Operations performed successfully")
conn.commit()
conn.close()