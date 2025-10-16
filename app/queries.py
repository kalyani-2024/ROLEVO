import os
import mysql.connector as ms
import traceback
import pandas as pd
from app import app
from flask import session

import os
from dotenv import load_dotenv

load_dotenv()

host = os.getenv('DB_HOST', 'localhost')
user = os.getenv('DB_USER', 'root')
password = os.getenv('DB_PASSWORD')
database = os.getenv('DB_NAME', 'roleplay')

def get_roleplay_details(roleplay_id):
    try:
        conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database
        )
        cur = conn.cursor()
        
        # Updated query to match MySQL table structure
        cur.execute("""
            SELECT name, file_path 
            FROM roleplay 
            WHERE id = %s
        """, (roleplay_id,))
        
        result = cur.fetchone()
        cur.close()
        conn.close()
        return result
    except Exception as e:
        print(f"Error getting roleplay details: {str(e)}")
        if 'conn' in locals():
            conn.close()
        return None

def create_or_update(id, name, person_name, scenario, roleplay_file_path, image_file_path):
    try:
        with ms.connect(host=host, user=user, password=password, database=database) as dbconn:
            cursor = dbconn.cursor()

            query = "SELECT file_path, image_file_path FROM roleplay WHERE id = %s"
            roleplay_id = id
            cursor.execute(query, (roleplay_id,))
            result = cursor.fetchone()

            if result:
                # Preserve existing file paths if new ones aren't provided
                if roleplay_file_path == '':
                    roleplay_file_path = result[0]
                if image_file_path == '':
                    image_file_path = result[1]

                update_query = (
                    "UPDATE roleplay SET name = %s, person_name = %s, scenario = %s, file_path = %s, image_file_path = %s WHERE id = %s"
                )
                cursor.execute(update_query, (name, person_name, scenario, roleplay_file_path, image_file_path, id))
                dbconn.commit()
                return id
            else:
                # Insert new row. If caller provided an id (alphanumeric), use it.
                if id:
                    insert_query = (
                        "INSERT INTO roleplay (id, name, person_name, scenario, file_path, image_file_path) VALUES (%s, %s, %s, %s, %s, %s)"
                    )
                    cursor.execute(insert_query, (id, name, person_name, scenario, roleplay_file_path, image_file_path))
                    dbconn.commit()
                    return id
                else:
                    insert_query = (
                        "INSERT INTO roleplay (name, person_name, scenario, file_path, image_file_path) VALUES (%s, %s, %s, %s, %s)"
                    )
                    cursor.execute(insert_query, (name, person_name, scenario, roleplay_file_path, image_file_path))
                    dbconn.commit()
                    new_id = cursor.lastrowid
                    return str(new_id)

    except Exception as e:
        print("Error in create_or_update:", str(e))
        traceback.print_exc()
        return None

def delete_roleplay(id):
    try:
        with ms.connect(host=host, user=user, password=password, database=database) as dbconn:
            cursor = dbconn.cursor()

            # Delete records from the "roleplay" table
            delete_query = "DELETE FROM roleplay WHERE id = %s"
            cursor.execute(delete_query, (id,))

            # Commit the transaction
            dbconn.commit()

            return True

    except:
        return None

import mysql.connector

def get_roleplay_file_path(roleplay_id):
    try:
        conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database
        )
        cur = conn.cursor()
        
        cur.execute("""
            SELECT file_path, scenario 
            FROM roleplay 
            WHERE id = %s
        """, (roleplay_id,))
        
        result = cur.fetchone()
        cur.close()
        conn.close()
        
        if result:
            # Convert to absolute paths
            excel_path = os.path.abspath(result[0])
            return excel_path, result[1]
        return None
        
    except mysql.connector.Error as e:
        print(f"Database error in get_roleplay_file_path: {e}")
        if 'conn' in locals():
            conn.close()
        return None

def get_roleplay(id):
    try:
        with ms.connect(host=host, user=user, password=password, database=database) as dbconn:
            cur = dbconn.cursor()
            query = "SELECT * FROM roleplay WHERE id = %s"
            cur.execute(query, (id,))
            result = cur.fetchone()
            return result
    except Exception as e:
        return None

def get_roleplays():
    try:
        with ms.connect(host=host, user=user, password=password, database=database) as dbconn:
            cur = dbconn.cursor()
            query = "SELECT * FROM roleplay"
            cur.execute(query)
            result = cur.fetchall()
            return result
    except Exception as e:
        return None

def get_user_id(email, password):
    try:
        with ms.connect(host=host, user=user, password=password, database=database) as dbconn:
            cursor = dbconn.cursor()
            query = "SELECT * FROM user WHERE email = %s"
            cursor.execute(query, (email,))
            row = cursor.fetchone()
            dbconn.close()

        if row:
            row_dict = {
                'id': row[0],
                'email': row[1],
                'password': row[2],
                'is_admin': row[3]
            }
            if hash.bcrypt.verify(password, str(row_dict['password'])):
                return {'id': row_dict['id'], 'is_admin': row_dict['is_admin']}

        return None
    except:
        return None

def query_update(roleplay_id):
    user_id = session["user_id"]

    dbconn = None
    cursor = None

    try:
        dbconn = ms.connect(host=host, user=user, password=password, database=database)
        cursor = dbconn.cursor()

        # Insert a new record into the "play" table
        insert_query = "INSERT INTO play (user_id, roleplay_id) VALUES (%s, %s)"
        cursor.execute(insert_query, (user_id, roleplay_id, ))

        # Retrieve the last inserted ID using lastrowid
        last_inserted_id = cursor.lastrowid

        # Commit the transaction
        dbconn.commit()

        session['play_id'] = last_inserted_id

        print("works")
    except Exception as e:
        # Rollback the transaction in case of an error
        print('reafhadsoifo herer')
        print(e)
        dbconn.rollback()

    finally:
        if cursor:
            cursor.close()
        if dbconn:
            dbconn.close()

def query_been_overriden(roleplay_obj):
    try:
        with ms.connect(host=host, user=user, password=password, database=database) as dbconn:

            user_id = session["user_id"]
            roleplay_id = roleplay_obj.id

            cursor = dbconn.cursor()
            query = "SELECT * FROM roleplayoverride WHERE user_id = %s AND roleplay_id = %s"
            cursor.execute(query, (user_id, roleplay_id,))
            rows = cursor.fetchall()
            dbconn.close()

        if rows:
            columns = [desc[0] for desc in cursor.description]
            df = pd.DataFrame(rows, columns=columns)
            cursor.close()
            dbconn.close()
            return df


        return None

    except:
        return None


def query_get_play_details(roleplay_obj):
    try:
        with ms.connect(host=host, user=user, password=password, database=database) as dbconn:

            user_id = session["user_id"]
            roleplay_id = roleplay_obj.id

            cursor = dbconn.cursor()
            query = "SELECT * FROM play WHERE user_id = %s AND roleplay_id = %s"
            cursor.execute(query, (user_id, roleplay_id,))
            rows = cursor.fetchall()

        if rows:
            columns = [desc[0] for desc in cursor.description]
            df = pd.DataFrame(rows, columns=columns)
            return df
        return None

    except:
        return None


def query_get_roleplays():
    try:
        with ms.connect(host=host, user=user, password=password, database=database) as dbconn:

            cursor = dbconn.cursor()
            query = "SELECT * FROM roleplay"
            cursor.execute(query)
            rows = cursor.fetchall()
            dbconn.close()

        if rows:
            columns = [desc[0] for desc in cursor.description]
            df = pd.DataFrame(rows, columns=columns)
            cursor.close()
            dbconn.close()
            return df
        return None

    except:
        return None

def get_play_info(play_id):
    try:
        with ms.connect(host=host, user=user, password=password, database=database) as dbconn:
            cur = dbconn.cursor()
            query = "SELECT * FROM play WHERE id = %s"
            cur.execute(query, (play_id,))
            result = cur.fetchone()
            return result
    except Exception as e:
        return None

def old_query_showreport(roleplay_id):
    user_id = session["user_id"]
    try:
        with ms.connect(host=host, user=user, password=password, database=database) as dbconn:
            # First query to retrieve play_id
            play_query = """
                SELECT * FROM play
                WHERE user_id = %s AND roleplay_id = %s
                ORDER BY id DESC
            """
            play_df = pd.read_sql_query(play_query, dbconn, params=(int(user_id), roleplay_id,))


            if not play_df.empty:
                play_id = play_df.iloc[0]['id']
                # Second query to retrieve play_data
                play_data_query = """
                    SELECT p.id AS play_id, ch.id AS chat_id, ch.user_text, ch.response_text, sm.overall_score, sb.score_name, sb.score
                    FROM play p
                    JOIN chathistory ch ON p.id = ch.play_id
                    JOIN scoremaster sm ON ch.id = sm.chathistory_id
                    JOIN scorebreakdown sb ON sm.id = sb.scoremaster_id
                    WHERE p.user_id = %s AND p.roleplay_id = %s AND p.id = %s
                    ORDER BY p.id DESC, ch.id ASC, sb.score_name
                """
                play_data_df = pd.read_sql_query(play_data_query, dbconn, params=(int(user_id), roleplay_id, int(play_id),))
        return play_data_df
    except Exception as e:
        print(e)
        return None


def query_showreport(play_id):
    try:
        with ms.connect(host=host, user=user, password=password, database=database) as dbconn:
            cur = dbconn.cursor()

            cur.execute("select * from chathistory where play_id=%s order by id asc", (play_id,))
            df = cur.fetchall()
            results = []
            for row in df:
                data = {}
                data["user"] = row[2]
                data["computer"] = row[3]


                cur.execute("select * from scoremaster where chathistory_id=%s", (row[0],))
                df2 = cur.fetchall()
                scoremaster_data = df2[0]
                data["score"] = scoremaster_data[2]

                cur.execute("select * from scorebreakdown where scoremaster_id=%s", (scoremaster_data[0],))
                df3 = cur.fetchall()

                scoredata = []
                for row2 in df3:
                    scoredata.append({"name": row2[1], "score": row2[2]})
                data["competencies"] = scoredata

                results.append(data)

            score_totals = {}
            for entry in results:
                for score in entry["competencies"]:
                    if score["name"] in score_totals:
                        score_totals[score["name"]]["score"] += score["score"]
                        score_totals[score["name"]]["total"] += 3
                    else:
                        score_totals[score["name"]] = {"score": score["score"], "total": 3}

            processed_score_totals = []
            for key in score_totals:
                processed_score_totals.append({"name": key, "score": score_totals[key]["score"], "total_possible": score_totals[key]["total"]})

            final_score = {"overall_score": {"score":0, "total":0}}
            for entry in results:
                final_score["overall_score"]["score"] += entry["score"]
                final_score["overall_score"]["total"] += 3

        return results, processed_score_totals, final_score
    except Exception as e:
        print(e, flush=True)
        return None


def query_create_chat_entry(user_text, response_text):
    try:
        if 'play_id' not in session:
            raise ValueError("No active play session")

        conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database
        )
        cur = conn.cursor()
        
        # Insert chat history with MySQL auto_increment
        cur.execute("""
            INSERT INTO chathistory (play_id, user_text, response_text) 
            VALUES (%s, %s, %s)
        """, (session['play_id'], user_text, response_text))
        
        conn.commit()
        chathistory_id = cur.lastrowid
        
        cur.close()
        conn.close()
        return chathistory_id

    except Exception as e:
        print(f"Error creating chat entry: {str(e)}")
        if 'conn' in locals():
            conn.close()
        return None

def query_create_score_master(chathistory_id, overall_score):
    try:
        with ms.connect(host=host, user=user, password=password, database=database) as dbconn:
                cursor = dbconn.cursor()

                # Insert a new record into the "scoremaster" table
                insert_query = "INSERT INTO scoremaster (chathistory_id, overall_score) VALUES (%s,%s)"
                insert_params = (chathistory_id, overall_score)
                cursor.execute(insert_query, insert_params)

                # Retrieve the last inserted ID
                last_insert_id_query = "SELECT LAST_INSERT_ID() AS id"
                cursor.execute(last_insert_id_query)
                scoremaster_id = cursor.fetchone()[0]

                # Commit the transaction
                dbconn.commit()
                return scoremaster_id

    except:
        return None

def query_create_score_breakdown(scoremaster_id, score_name, score):
    try:
        with ms.connect(host=host, user=user, password=password, database=database) as dbconn:
                cursor = dbconn.cursor()

                # Insert a new record into the "scorebreakdown" table
                insert_query = "INSERT INTO scorebreakdown (scoremaster_id, score_name, score) VALUES (%s,%s,%s)"
                cursor.execute(insert_query, (scoremaster_id, score_name, score,))

                # Commit the transaction
                dbconn.commit()

    except:
        return None

def query_end_attempts():
    roleplay_id = session["roleplay_id"]
    user_id = session["user_id"]
    try:
        with ms.connect(host=host, user=user, password=password, database=database) as dbconn:
                cursor = dbconn.cursor()

                # Insert a new record into the "roleplayoverride" table
                insert_query = "INSERT INTO roleplayoverride (roleplay_id, user_id) VALUES (%s,%s)"
                cursor.execute(insert_query, (roleplay_id, user_id,))

                # Commit the transaction
                dbconn.commit()

    except:
        return None

def query_email_data(email_input_add):
    try:
        with ms.connect(host=host, user=user, password=password, database=database) as dbconn:
                cursor = dbconn.cursor()

                # Execute the SELECT query
                query = "SELECT * FROM user WHERE email = %s"
                cursor.execute(query, (email_input_add,))

                # Fetch the results
                results = cursor.fetchall()

                # Convert the results to a DataFrame
                columns = [desc[0] for desc in cursor.description]
                df = pd.DataFrame(results, columns=columns)
                return df

    except:
        return None

def query_add_user(email_input_add, hashed_password, is_user_admin):
    try:
        with ms.connect(host=host, user=user, password=password, database=database) as dbconn:
                cursor = dbconn.cursor()

                # Insert a new record into the "user" table
                insert_query = "INSERT INTO user (email, password, is_admin) VALUES (%s, %s, %s)"
                cursor.execute(insert_query, (email_input_add, hashed_password, is_user_admin,))

                # Commit the transaction
                dbconn.commit()

    except:
        return None

def query_delete_user(email_input_delete):
    try:
        with ms.connect(host=host, user=user, password=password, database=database) as dbconn:
                cursor = dbconn.cursor()

                # Delete records from the "user" table
                delete_query = "DELETE FROM user WHERE email = %s"
                cursor.execute(delete_query, (email_input_delete,))

                # Commit the transaction
                dbconn.commit()

    except:
        return None

def query_name_data(roleplay_input):
    try:
        with ms.connect(host=host, user=user, password=password, database=database) as dbconn:
                cursor = dbconn.cursor()

                # Execute the SELECT query
                query = "SELECT * FROM roleplay WHERE name = %s"
                cursor.execute(query, (roleplay_input,))

                # Fetch the results
                results = cursor.fetchall()

                # Convert the results to a DataFrame
                columns = [desc[0] for desc in cursor.description]
                df = pd.DataFrame(results, columns=columns)
                return df


    except:
        return None

def query_add_roleplay(roleplay_input, save_path):
    try:
        with ms.connect(host=host, user=user, password=password, database=database) as dbconn:
                cursor = dbconn.cursor()

                # Insert a new record into the "roleplay" table
                insert_query = "INSERT INTO roleplay (name, file_path) VALUES (%s, %s)"
                cursor.execute(insert_query, (roleplay_input, save_path,))

                # Commit the transaction
                dbconn.commit()

    except:
        return None

# New functions for enhanced roleplay configuration

def create_or_update_roleplay_config(roleplay_id, config_data):
    """Create or update roleplay configuration"""
    try:
        with ms.connect(host=host, user=user, password=password, database=database) as dbconn:
            cursor = dbconn.cursor()
            
            # Check if config exists
            cursor.execute("SELECT id FROM roleplay_config WHERE roleplay_id = %s", (roleplay_id,))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing configuration
                update_query = """
                UPDATE roleplay_config SET 
                    input_type = %s,
                    audio_rerecord_attempts = %s,
                    available_languages = %s,
                    max_interaction_time = %s,
                    max_total_time = %s,
                    repeat_attempts_allowed = %s,
                    score_type = %s,
                    show_ideal_video = %s,
                    ideal_video_path = %s,
                    voice_assessment_enabled = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE roleplay_id = %s
                """
                cursor.execute(update_query, (
                    config_data['input_type'],
                    config_data['audio_rerecord_attempts'],
                    config_data['available_languages'],
                    config_data['max_interaction_time'],
                    config_data['max_total_time'],
                    config_data['repeat_attempts_allowed'],
                    config_data['score_type'],
                    config_data['show_ideal_video'],
                    config_data.get('ideal_video_path', ''),
                    config_data['voice_assessment_enabled'],
                    roleplay_id
                ))
            else:
                # Create new configuration
                insert_query = """
                INSERT INTO roleplay_config (
                    roleplay_id, input_type, audio_rerecord_attempts, available_languages,
                    max_interaction_time, max_total_time, repeat_attempts_allowed,
                    score_type, show_ideal_video, ideal_video_path, voice_assessment_enabled
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(insert_query, (
                    roleplay_id,
                    config_data['input_type'],
                    config_data['audio_rerecord_attempts'],
                    config_data['available_languages'],
                    config_data['max_interaction_time'],
                    config_data['max_total_time'],
                    config_data['repeat_attempts_allowed'],
                    config_data['score_type'],
                    config_data['show_ideal_video'],
                    config_data.get('ideal_video_path', ''),
                    config_data['voice_assessment_enabled']
                ))
            
            dbconn.commit()
            return True
    except Exception as e:
        print(f"Error creating/updating roleplay config: {str(e)}")
        return False

def get_roleplay_config(roleplay_id):
    """Get roleplay configuration"""
    try:
        with ms.connect(host=host, user=user, password=password, database=database) as dbconn:
            cursor = dbconn.cursor()
            cursor.execute("SELECT * FROM roleplay_config WHERE roleplay_id = %s", (roleplay_id,))
            return cursor.fetchone()
    except Exception as e:
        print(f"Error getting roleplay config: {str(e)}")
        return None

def get_roleplay_with_config(roleplay_id):
    """Get roleplay with its configuration"""
    try:
        with ms.connect(host=host, user=user, password=password, database=database) as dbconn:
            cursor = dbconn.cursor()
            query = """
            SELECT r.*, rc.input_type, rc.audio_rerecord_attempts, rc.available_languages,
                   rc.max_interaction_time, rc.max_total_time, rc.repeat_attempts_allowed,
                   rc.score_type, rc.show_ideal_video, rc.ideal_video_path, rc.voice_assessment_enabled
            FROM roleplay r
            LEFT JOIN roleplay_config rc ON r.id = rc.roleplay_id
            WHERE r.id = %s
            """
            cursor.execute(query, (roleplay_id,))
            return cursor.fetchone()
    except Exception as e:
        print(f"Error getting roleplay with config: {str(e)}")
        return None

# Cluster management functions

def create_cluster(name, cluster_id=None, cluster_type='assessment'):
    """Create a new roleplay cluster. If cluster_id not provided, auto-generate a short uuid."""
    try:
        import uuid
        if not cluster_id:
            cluster_id = str(uuid.uuid4())[:12]
        with ms.connect(host=host, user=user, password=password, database=database) as dbconn:
            cursor = dbconn.cursor()
            insert_query = """
            INSERT INTO roleplay_cluster (name, cluster_id, type) 
            VALUES (%s, %s, %s)
            """
            cursor.execute(insert_query, (name, cluster_id, cluster_type))
            dbconn.commit()
            return cursor.lastrowid
    except Exception as e:
        print(f"Error creating cluster: {str(e)}")
        return None

def get_clusters():
    """Get all clusters"""
    try:
        with ms.connect(host=host, user=user, password=password, database=database) as dbconn:
            cursor = dbconn.cursor()
            cursor.execute("SELECT * FROM roleplay_cluster ORDER BY created_at DESC")
            return cursor.fetchall()
    except Exception as e:
        print(f"Error getting clusters: {str(e)}")
        return []

def get_cluster(cluster_id):
    """Get specific cluster"""
    try:
        with ms.connect(host=host, user=user, password=password, database=database) as dbconn:
            cursor = dbconn.cursor()
            cursor.execute("SELECT * FROM roleplay_cluster WHERE id = %s", (cluster_id,))
            return cursor.fetchone()
    except Exception as e:
        print(f"Error getting cluster: {str(e)}")
        return None

def add_roleplay_to_cluster(cluster_id, roleplay_id, order_sequence=1):
    """Add roleplay to cluster"""
    try:
        with ms.connect(host=host, user=user, password=password, database=database) as dbconn:
            cursor = dbconn.cursor()
            insert_query = """
            INSERT INTO cluster_roleplay (cluster_id, roleplay_id, order_sequence) 
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE order_sequence = %s
            """
            cursor.execute(insert_query, (cluster_id, roleplay_id, order_sequence, order_sequence))
            dbconn.commit()
            return True
    except Exception as e:
        print(f"Error adding roleplay to cluster: {str(e)}")
        return False

def remove_roleplay_from_cluster(cluster_id, roleplay_id):
    """Remove roleplay from cluster"""
    try:
        with ms.connect(host=host, user=user, password=password, database=database) as dbconn:
            cursor = dbconn.cursor()
            cursor.execute("DELETE FROM cluster_roleplay WHERE cluster_id = %s AND roleplay_id = %s", 
                         (cluster_id, roleplay_id))
            dbconn.commit()
            return True
    except Exception as e:
        print(f"Error removing roleplay from cluster: {str(e)}")
        return False

def get_cluster_roleplays(cluster_id):
    """Get all roleplays in a cluster"""
    try:
        with ms.connect(host=host, user=user, password=password, database=database) as dbconn:
            cursor = dbconn.cursor()
            query = """
            SELECT r.*, cr.order_sequence
            FROM roleplay r
            JOIN cluster_roleplay cr ON r.id = cr.roleplay_id
            WHERE cr.cluster_id = %s
            ORDER BY cr.order_sequence
            """
            cursor.execute(query, (cluster_id,))
            return cursor.fetchall()
    except Exception as e:
        print(f"Error getting cluster roleplays: {str(e)}")
        return []

def delete_cluster(cluster_id):
    """Delete a cluster and its associations"""
    try:
        with ms.connect(host=host, user=user, password=password, database=database) as dbconn:
            cursor = dbconn.cursor()
            # Delete cluster (cascade will handle cluster_roleplay)
            cursor.execute("DELETE FROM roleplay_cluster WHERE id = %s", (cluster_id,))
            dbconn.commit()
            return True
    except Exception as e:
        print(f"Error deleting cluster: {str(e)}")
        return False
