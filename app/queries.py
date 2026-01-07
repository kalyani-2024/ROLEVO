import os
import mysql.connector as ms
import traceback
import pandas as pd
import warnings
from app import app
from flask import session
import bcrypt
import secrets
import string
import re

import os
from dotenv import load_dotenv

# Suppress pandas SQLAlchemy warnings for mysql.connector usage
warnings.filterwarnings('ignore', message='.*pandas only supports SQLAlchemy.*')

load_dotenv()

host = os.getenv('DB_HOST', 'localhost')
user = os.getenv('DB_USER', 'root')
password = os.getenv('DB_PASSWORD')
database = os.getenv('DB_NAME', 'roleplay')

def validate_password(password):
    """
    Validate password against policy requirements:
    - Minimum 8 characters
    - At least 1 uppercase letter
    - At least 1 numeric digit
    - At least 1 special character
    
    Returns: (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least 1 uppercase letter"
    
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least 1 numeric digit"
    
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};:\'",.<>?/\\|`~]', password):
        return False, "Password must contain at least 1 special character"
    
    return True, "Password is valid"

def generate_unique_roleplay_id():
    """Generate a unique alphanumeric ID for roleplay"""
    while True:
        # Generate a random alphanumeric ID (e.g., RP_A7B9C2D4)
        random_part = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
        new_id = f"RP_{random_part}"
        
        # Check if this ID already exists
        try:
            with ms.connect(host=host, user=user, password=password, database=database) as dbconn:
                cursor = dbconn.cursor()
                cursor.execute("SELECT id FROM roleplay WHERE id = %s", (new_id,))
                if cursor.fetchone() is None:
                    return new_id
        except:
            # If there's an error, generate a new ID
            continue

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

def create_or_update(id, name, person_name, scenario, roleplay_file_path, image_file_path, competency_file_path='', scenario_file_path='', logo_path=''):
    try:
        with ms.connect(host=host, user=user, password=password, database=database) as dbconn:
            cursor = dbconn.cursor()

            query = "SELECT file_path, image_file_path, competency_file_path, scenario_file_path, logo_path FROM roleplay WHERE id = %s"
            roleplay_id = id
            cursor.execute(query, (roleplay_id,))
            result = cursor.fetchone()

            if result:
                # Preserve existing file paths if new ones aren't provided
                if roleplay_file_path == '':
                    roleplay_file_path = result[0]
                if image_file_path == '':
                    image_file_path = result[1]
                if competency_file_path == '':
                    competency_file_path = result[2] if result[2] else ''
                if scenario_file_path == '':
                    scenario_file_path = result[3] if result[3] else ''
                if logo_path == '':
                    logo_path = result[4] if result[4] else ''

                update_query = (
                    "UPDATE roleplay SET name = %s, person_name = %s, scenario = %s, file_path = %s, image_file_path = %s, competency_file_path = %s, scenario_file_path = %s, logo_path = %s WHERE id = %s"
                )
                cursor.execute(update_query, (name, person_name, scenario, roleplay_file_path, image_file_path, competency_file_path, scenario_file_path, logo_path, id))
                dbconn.commit()
                return id
            else:
                # Insert new row
                # Generate alphanumeric ID if not provided
                if not id:
                    id = generate_unique_roleplay_id()
                
                insert_query = (
                    "INSERT INTO roleplay (id, name, person_name, scenario, file_path, image_file_path, competency_file_path, scenario_file_path, logo_path) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
                )
                cursor.execute(insert_query, (id, name, person_name, scenario, roleplay_file_path, image_file_path, competency_file_path, scenario_file_path, logo_path))
                dbconn.commit()
                return id

    except Exception as e:
        print("Error in create_or_update:", str(e))
        traceback.print_exc()
        return None

def delete_roleplay(id):
    try:
        with ms.connect(host=host, user=user, password=password, database=database) as dbconn:
            cursor = dbconn.cursor()

            # Delete related records first to avoid foreign key constraint violations
            # Delete all play records for this roleplay
            cursor.execute("DELETE FROM play WHERE roleplay_id = %s", (id,))
            
            # Delete cluster associations (cluster_roleplay table)
            cursor.execute("DELETE FROM cluster_roleplay WHERE roleplay_id = %s", (id,))
            
            # Delete roleplay config (if not using ON DELETE CASCADE)
            cursor.execute("DELETE FROM roleplay_config WHERE roleplay_id = %s", (id,))
            
            # Delete roleplay overrides (if not using ON DELETE CASCADE)
            cursor.execute("DELETE FROM roleplayoverride WHERE roleplay_id = %s", (id,))
            
            # Finally, delete the roleplay itself
            cursor.execute("DELETE FROM roleplay WHERE id = %s", (id,))

            # Commit the transaction
            dbconn.commit()

            return True

    except Exception as e:
        print(f"Error deleting roleplay {id}: {str(e)}")
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

def get_user_id(email, user_password):
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
            # Verify password using bcrypt directly
            password_bytes = user_password.encode('utf-8')
            hashed_password = row_dict['password'].encode('utf-8')
            if bcrypt.checkpw(password_bytes, hashed_password):
                return {'id': row_dict['id'], 'is_admin': row_dict['is_admin']}

        return None
    except Exception as e:
        print(f"Login error: {str(e)}")
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
            
            # First, get the roleplay_id and file path to read Tags sheet
            cur.execute("SELECT roleplay_id FROM play WHERE id=%s", (play_id,))
            play_result = cur.fetchone()
            roleplay_id = play_result[0] if play_result else None
            
            # Get max scores from Excel Tags sheet
            max_scores_dict = {}
            if roleplay_id:
                file_info = get_roleplay_file_path(roleplay_id)
                if file_info:
                    excel_path = file_info[0]
                    
                    # First, load the master/metacompetency file to get abbreviation mapping and descriptions
                    abbr_to_full_name = {}
                    full_name_to_abbr = {}
                    competency_descriptions = {}  # Store descriptions for report
                    try:
                        # Get the competency file path from roleplay table
                        cur.execute("SELECT competency_file_path FROM roleplay WHERE id=%s", (roleplay_id,))
                        comp_result = cur.fetchone()
                        if comp_result and comp_result[0]:
                            comp_file_path = os.path.abspath(comp_result[0])
                            
                            # Load master file to get abbreviation -> full name mapping and descriptions
                            import pandas as pd
                            import re
                            comp_xls = pd.ExcelFile(comp_file_path)
                            comp_data = comp_xls.parse(0)  # First sheet
                            
                            # Create mapping: Abbr -> CompetencyType (full name) and reverse
                            if 'Abbr' in comp_data.columns and 'CompetencyType' in comp_data.columns:
                                for _, row in comp_data.iterrows():
                                    abbr = row.get('Abbr')
                                    full_name = row.get('CompetencyType')
                                    description = row.get('Description', '')
                                    if pd.notna(abbr) and pd.notna(full_name):
                                        abbr_str = str(abbr).strip().upper()
                                        full_name_str = str(full_name).strip()
                                        
                                        # Store with full abbr (e.g., "MOTVN LEVEL 2")
                                        abbr_to_full_name[abbr_str] = full_name_str
                                        full_name_to_abbr[full_name_str.lower()] = abbr_str
                                        
                                        # Also extract base abbr without "LEVEL X" (e.g., "MOTVN")
                                        base_abbr = re.sub(r'\s*LEVEL\s*\d+\s*$', '', abbr_str, flags=re.IGNORECASE).strip()
                                        if base_abbr != abbr_str:
                                            abbr_to_full_name[base_abbr] = full_name_str
                                        
                                        if pd.notna(description):
                                            competency_descriptions[full_name_str] = str(description).strip()
                    except Exception as e:
                        pass  # Continue with empty dict
                    
                    try:
                        # Read Tags sheet to get Max Score for each competency
                        import pandas as pd
                        xls = pd.ExcelFile(excel_path)
                        tags_sheet = None
                        for sheet in xls.sheet_names:
                            if "tags" in sheet.lower():
                                tags_sheet = sheet
                                break
                        
                        if tags_sheet:
                            # Read the entire sheet without treating first row as header
                            tag_data = xls.parse(tags_sheet, header=None)
                            
                            # Find the row that contains "Competenc" (matches Competency/Competencies) and "max" + "score"
                            header_row_idx = None
                            for idx in range(len(tag_data)):
                                row_values = tag_data.iloc[idx].astype(str).str.lower().tolist()
                                # More flexible: match "competenc" (covers competency/competencies) and "max" with "score" (covers "max score"/"max scores")
                                has_competency = any('competenc' in str(v).lower() for v in row_values)
                                has_max_score = any('max' in str(v).lower() for v in row_values)
                                
                                if has_competency and has_max_score:
                                    header_row_idx = idx
                                    break
                            
                            if header_row_idx is not None:
                                # Re-parse with correct header row
                                tag_data = xls.parse(tags_sheet, header=header_row_idx)
                                
                                # Build dictionary: competency_name -> max_score
                                for idx, row in tag_data.iterrows():
                                    # Get Enabled value - try different column names
                                    enabled = None
                                    for col in ['Enabled', 'enabled', tag_data.columns[2] if len(tag_data.columns) > 2 else None]:
                                        if col and col in tag_data.columns:
                                            enabled = row.get(col)
                                            if pd.notna(enabled):
                                                break
                                    
                                    # Try different possible column names for the competency identifier
                                    comp_name = None
                                    for col in ['Competencies', 'Competency', 'competencies', 'competency', 'Competency Name', 'Name', tag_data.columns[0]]:
                                        if col and col in tag_data.columns:
                                            comp_name = row.get(col)
                                            if pd.notna(comp_name):
                                                break
                                    
                                    # Try different column names for max score
                                    max_score = None
                                    for col in ['max scores', 'Max scores', 'Max Score', 'Max score', 'max score', 'MaxScore', 'MaxScores', tag_data.columns[1] if len(tag_data.columns) > 1 else None]:
                                        if col and col in tag_data.columns:
                                            max_score = row.get(col)
                                            if pd.notna(max_score):
                                                break
                                    
                                    # Accept if either Enabled='Y' OR if enabled is None/NaN (for sheets without Enabled column)
                                    # Check both enabled is None and pd.isna(enabled) to handle all cases
                                    enabled_ok = (enabled == 'Y' or enabled is None or pd.isna(enabled))
                                    
                                    if comp_name and pd.notna(max_score) and enabled_ok:
                                        comp_name_str = str(comp_name).strip()
                                        try:
                                            max_score_int = int(float(max_score))  # Handle both int and float strings
                                        except (ValueError, TypeError):
                                            continue
                                        
                                        # Store with abbreviation from Tags sheet (e.g., "MOTVN LEVEL 2")
                                        max_scores_dict[comp_name_str] = max_score_int
                                        max_scores_dict[comp_name_str.lower()] = max_score_int
                                        
                                        # Extract base abbreviation by removing "LEVEL X" suffix
                                        # e.g., "MOTVN LEVEL 2" -> "MOTVN"
                                        import re
                                        base_abbr = re.sub(r'\s*LEVEL\s*\d+\s*$', '', comp_name_str, flags=re.IGNORECASE).strip().upper()
                                        
                                        # Map base abbreviation to full name from master file
                                        if base_abbr in abbr_to_full_name:
                                            full_name = abbr_to_full_name[base_abbr]
                                            max_scores_dict[full_name] = max_score_int
                                            max_scores_dict[full_name.lower()] = max_score_int
                            else:
                                pass  # No header row found
                                    
                        else:
                            pass  # No Tags sheet found
                    except Exception as e:
                        pass  # Continue with empty dict

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
                    # row2[0]=id, row2[1]=scoremaster_id, row2[2]=score_name, row2[3]=score
                    scoredata.append({"name": row2[2], "score": row2[3]})
                data["competencies"] = scoredata

                results.append(data)

            score_totals = {}
            for entry in results:
                for score in entry["competencies"]:
                    comp_name = score["name"]
                    
                    if comp_name in score_totals:
                        score_totals[comp_name]["score"] += score["score"]
                        # Cap at the max to prevent exceeding Tags sheet limit
                        if score_totals[comp_name]["score"] > score_totals[comp_name]["total"]:
                            score_totals[comp_name]["score"] = score_totals[comp_name]["total"]
                        # Don't add to total - it's already the final max from Tags sheet
                    else:
                        # Get max score from Tags sheet - try multiple matching strategies
                        max_score_total = None
                        matched_key = None
                        
                        # Strategy 1: Exact match
                        if comp_name in max_scores_dict:
                            max_score_total = max_scores_dict[comp_name]
                            matched_key = comp_name
                        
                        # Strategy 2: Case-insensitive match
                        if max_score_total is None:
                            for key in max_scores_dict.keys():
                                if key.lower() == comp_name.lower():
                                    max_score_total = max_scores_dict[key]
                                    matched_key = key
                                    break
                        
                        # Strategy 3: Partial match - check if Tags key contains part of comp_name or vice versa
                        if max_score_total is None:
                            # Extract base competency name (remove "Level X" and common suffixes)
                            import re
                            comp_base = re.sub(r'\s*Level\s*\d+\s*', '', comp_name, flags=re.IGNORECASE).strip()
                            comp_base = comp_base.replace('-', '').replace('/', '').lower()
                            
                            for key in max_scores_dict.keys():
                                key_base = re.sub(r'\s*Level\s*\d+\s*', '', key, flags=re.IGNORECASE).strip()
                                key_base = key_base.replace('-', '').replace('/', '').lower()
                                
                                # Check for partial matches (e.g., "persuasion" matches "persuade")
                                if comp_base in key_base or key_base in comp_base:
                                    max_score_total = max_scores_dict[key]
                                    matched_key = key
                                    break
                        
                        # Skip competencies not found in Tags sheet (don't include in report)
                        if max_score_total is None:
                            continue
                        
                        score_totals[comp_name] = {"score": score["score"], "total": max_score_total}

            # Final pass: ensure no scores exceed their maximums
            processed_score_totals = []
            for key in score_totals:
                final_score_value = score_totals[key]["score"]
                max_allowed = score_totals[key]["total"]
                
                # Cap score at maximum if it exceeds
                if final_score_value > max_allowed:
                    final_score_value = max_allowed
                
                # Get description from master file
                description = competency_descriptions.get(key, '')
                
                processed_score_totals.append({
                    "name": key, 
                    "score": final_score_value, 
                    "total_possible": max_allowed,
                    "description": description
                })

            final_score = {"overall_score": {"score":0, "total":0}}
            for entry in results:
                final_score["overall_score"]["score"] += entry["score"]
                final_score["overall_score"]["total"] += 3

        return results, processed_score_totals, final_score
    except Exception as e:
        print(f"Error in query_showreport: {e}", flush=True)
        return None


def mark_play_completed(play_id):
    """Mark a play session as completed"""
    try:
        conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database
        )
        cur = conn.cursor()
        
        # Update play status to completed and set end time
        cur.execute("""
            UPDATE play 
            SET status = 'completed', end_time = NOW()
            WHERE id = %s
        """, (play_id,))
        
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error marking play as completed: {e}")
        return False


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
                    difficulty_level = %s,
                    enable_16pf_analysis = %s,
                    pf16_analysis_source = %s,
                    pf16_user_age_required = %s,
                    pf16_user_gender_required = %s,
                    pf16_default_age = %s,
                    pf16_send_audio_for_analysis = %s,
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
                    config_data.get('difficulty_level', 'easy'),
                    config_data.get('enable_16pf_analysis', False),
                    config_data.get('pf16_analysis_source', 'none'),
                    config_data.get('pf16_user_age_required', True),
                    config_data.get('pf16_user_gender_required', True),
                    config_data.get('pf16_default_age', 30),
                    config_data.get('pf16_send_audio_for_analysis', True),
                    roleplay_id
                ))
            else:
                # Create new configuration
                insert_query = """
                INSERT INTO roleplay_config (
                    roleplay_id, input_type, audio_rerecord_attempts, available_languages,
                    max_interaction_time, max_total_time, repeat_attempts_allowed,
                    score_type, show_ideal_video, ideal_video_path, voice_assessment_enabled,
                    difficulty_level, enable_16pf_analysis, pf16_analysis_source,
                    pf16_user_age_required, pf16_user_gender_required, pf16_default_age,
                    pf16_send_audio_for_analysis
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                    config_data['voice_assessment_enabled'],
                    config_data.get('difficulty_level', 'easy'),
                    config_data.get('enable_16pf_analysis', False),
                    config_data.get('pf16_analysis_source', 'none'),
                    config_data.get('pf16_user_age_required', True),
                    config_data.get('pf16_user_gender_required', True),
                    config_data.get('pf16_default_age', 30),
                    config_data.get('pf16_send_audio_for_analysis', True)
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

def update_cluster(id, name, cluster_type='assessment'):
    """Update an existing roleplay cluster's name and type"""
    try:
        with ms.connect(host=host, user=user, password=password, database=database) as dbconn:
            cursor = dbconn.cursor()
            update_query = """
            UPDATE roleplay_cluster 
            SET name = %s, type = %s
            WHERE id = %s
            """
            cursor.execute(update_query, (name, cluster_type, id))
            dbconn.commit()
            return True
    except Exception as e:
        print(f"Error updating cluster: {str(e)}")
        return False

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
            # First check if cluster_roleplay entries exist
            cursor.execute("SELECT COUNT(*) FROM cluster_roleplay WHERE cluster_id = %s", (cluster_id,))
            count = cursor.fetchone()[0]
            
            query = """
            SELECT r.*, cr.order_sequence
            FROM roleplay r
            JOIN cluster_roleplay cr ON r.id = cr.roleplay_id
            WHERE cr.cluster_id = %s
            ORDER BY cr.order_sequence
            """
            cursor.execute(query, (cluster_id,))
            results = cursor.fetchall()
            return results
    except Exception as e:
        print(f"Error getting cluster roleplays: {str(e)}")
        return []

def delete_cluster(cluster_id):
    """Delete a cluster and its associations"""
    try:
        with ms.connect(host=host, user=user, password=password, database=database) as dbconn:
            cursor = dbconn.cursor()
            
            # Step 1: Delete or nullify play records that reference this cluster
            # Option A: Set cluster_id to NULL (preserve play history)
            cursor.execute("UPDATE play SET cluster_id = NULL WHERE cluster_id = %s", (cluster_id,))
            print(f"Updated {cursor.rowcount} play records to remove cluster reference")
            
            # Option B: If you want to delete play records entirely (uncomment if needed):
            # cursor.execute("DELETE FROM play WHERE cluster_id = %s", (cluster_id,))
            # print(f"Deleted {cursor.rowcount} play records")
            
            # Step 2: Delete user_cluster associations (users assigned to this cluster)
            cursor.execute("DELETE FROM user_cluster WHERE cluster_id = %s", (cluster_id,))
            print(f"Deleted {cursor.rowcount} user_cluster associations")
            
            # Step 3: Delete cluster_roleplay associations (cascade should handle this, but explicit is safer)
            cursor.execute("DELETE FROM cluster_roleplay WHERE cluster_id = %s", (cluster_id,))
            print(f"Deleted {cursor.rowcount} cluster_roleplay associations")
            
            # Step 4: Finally delete the cluster itself
            cursor.execute("DELETE FROM roleplay_cluster WHERE id = %s", (cluster_id,))
            print(f"Deleted cluster with id={cluster_id}")
            
            dbconn.commit()
            return True
    except Exception as e:
        print(f"Error deleting cluster: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

# User Management Functions

def get_all_users():
    """Get all users from the database"""
    try:
        with ms.connect(host=host, user=user, password=password, database=database) as dbconn:
            cursor = dbconn.cursor()
            cursor.execute("""
                SELECT id, email, is_admin 
                FROM user 
                ORDER BY id DESC
            """)
            return cursor.fetchall()
    except Exception as e:
        print(f"Error getting users: {str(e)}")
        return []

def get_user(user_id):
    """Get a single user by ID"""
    try:
        with ms.connect(host=host, user=user, password=password, database=database) as dbconn:
            cursor = dbconn.cursor()
            cursor.execute("SELECT id, email, is_admin FROM user WHERE id = %s", (user_id,))
            return cursor.fetchone()
    except Exception as e:
        print(f"Error getting user: {str(e)}")
        return None

def create_user_account(email, password_plain):
    """Create a new user account"""
    try:
        # Hash the password using bcrypt
        password_bytes = password_plain.encode('utf-8')
        salt = bcrypt.gensalt(rounds=12)
        password_hash = bcrypt.hashpw(password_bytes, salt)
        
        with ms.connect(host=host, user=user, password=password, database=database) as dbconn:
            cursor = dbconn.cursor()
            
            # Check if email already exists
            cursor.execute("SELECT id FROM user WHERE email = %s", (email,))
            if cursor.fetchone():
                return None, "Email already registered"
            
            # Insert new user (bcrypt hash is bytes, MySQL expects string)
            cursor.execute("""
                INSERT INTO user (email, password, is_admin) 
                VALUES (%s, %s, 0)
            """, (email, password_hash.decode('utf-8')))
            dbconn.commit()
            
            return cursor.lastrowid, "Success"
    except Exception as e:
        print(f"Error creating user: {str(e)}")
        return None, str(e)

def get_user_by_email(email):
    """Get user by email"""
    try:
        with ms.connect(host=host, user=user, password=password, database=database) as dbconn:
            cursor = dbconn.cursor()
            cursor.execute("SELECT id, email, is_admin FROM user WHERE email = %s", (email,))
            return cursor.fetchone()
    except Exception as e:
        print(f"Error getting user by email: {str(e)}")
        return None

def create_user(email, password_plain, username, is_admin=False):
    """Create a new user account (regular or admin)"""
    try:
        # Hash the password using bcrypt
        password_bytes = password_plain.encode('utf-8')
        salt = bcrypt.gensalt(rounds=12)
        password_hash = bcrypt.hashpw(password_bytes, salt)
        
        with ms.connect(host=host, user=user, password=password, database=database) as dbconn:
            cursor = dbconn.cursor()
            
            # Check if email already exists
            cursor.execute("SELECT id FROM user WHERE email = %s", (email,))
            if cursor.fetchone():
                return None
            
            # Insert new user (bcrypt hash is bytes, MySQL expects string)
            admin_flag = 1 if is_admin else 0
            cursor.execute("""
                INSERT INTO user (email, password, is_admin) 
                VALUES (%s, %s, %s)
            """, (email, password_hash.decode('utf-8'), admin_flag))
            dbconn.commit()
            
            return cursor.lastrowid
    except Exception as e:
        print(f"Error creating user: {str(e)}")
        return None

def assign_cluster_to_user(user_id, cluster_id):
    """Assign a cluster to a user"""
    try:
        with ms.connect(host=host, user=user, password=password, database=database) as dbconn:
            cursor = dbconn.cursor()
            # Check if assignment already exists
            cursor.execute("""
                SELECT user_id FROM user_cluster 
                WHERE user_id = %s AND cluster_id = %s
            """, (user_id, cluster_id))
            if cursor.fetchone():
                return True  # Already assigned
            
            cursor.execute("""
                INSERT INTO user_cluster (user_id, cluster_id) 
                VALUES (%s, %s)
            """, (user_id, cluster_id))
            dbconn.commit()
            return True
    except Exception as e:
        print(f"Error assigning cluster to user: {str(e)}")
        return False

def remove_cluster_from_user(user_id, cluster_id):
    """Remove a cluster assignment from a user"""
    try:
        with ms.connect(host=host, user=user, password=password, database=database) as dbconn:
            cursor = dbconn.cursor()
            cursor.execute("""
                DELETE FROM user_cluster 
                WHERE user_id = %s AND cluster_id = %s
            """, (user_id, cluster_id))
            dbconn.commit()
            return True
    except Exception as e:
        print(f"Error removing cluster from user: {str(e)}")
        return False

def get_user_clusters(user_id):
    """Get all clusters assigned to a user"""
    try:
        with ms.connect(host=host, user=user, password=password, database=database) as dbconn:
            cursor = dbconn.cursor()
            
            # First check if user has any cluster assignments
            cursor.execute("SELECT COUNT(*) FROM user_cluster WHERE user_id = %s", (user_id,))
            count = cursor.fetchone()[0]
            
            # Get the cluster details
            cursor.execute("""
                SELECT rc.id, rc.name, rc.cluster_id, rc.type, rc.created_at
                FROM roleplay_cluster rc
                INNER JOIN user_cluster uc ON rc.id = uc.cluster_id
                WHERE uc.user_id = %s
                ORDER BY rc.created_at DESC
            """, (user_id,))
            results = cursor.fetchall()
            return results
    except Exception as e:
        print(f"Error getting user clusters: {str(e)}")
        return []

def get_cluster_users(cluster_id):
    """Get all users assigned to a cluster"""
    try:
        with ms.connect(host=host, user=user, password=password, database=database) as dbconn:
            cursor = dbconn.cursor()
            cursor.execute("""
                SELECT u.id, u.email, u.name, u.created_at
                FROM user u
                INNER JOIN user_cluster uc ON u.id = uc.user_id
                WHERE uc.cluster_id = %s
                ORDER BY u.name
            """, (cluster_id,))
            return cursor.fetchall()
    except Exception as e:
        print(f"Error getting cluster users: {str(e)}")
        return []


# =============================================
# 16PF Voice Analysis Functions
# =============================================

def save_16pf_analysis_result(play_id, user_id, roleplay_id, audio_file_path,
                               user_age=None, user_gender=None, analysis_source='persona360'):
    """Create a pending 16PF analysis record"""
    try:
        with ms.connect(host=host, user=user, password=password, database=database) as dbconn:
            cursor = dbconn.cursor()
            cursor.execute("""
                INSERT INTO pf16_analysis_results 
                (play_id, user_id, roleplay_id, audio_file_path, analysis_source, 
                 user_age, user_gender, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending')
            """, (play_id, user_id, roleplay_id, audio_file_path, 
                  analysis_source, user_age, user_gender))
            dbconn.commit()
            return cursor.lastrowid
    except Exception as e:
        print(f"Error saving 16PF analysis record: {str(e)}")
        return None


def update_16pf_analysis_result(analysis_id, status, raw_response=None, 
                                 personality_scores=None, composite_scores=None,
                                 overall_role_fit=None, analysis_confidence=None,
                                 error_message=None):
    """Update a 16PF analysis record with results or error"""
    import json
    try:
        with ms.connect(host=host, user=user, password=password, database=database) as dbconn:
            cursor = dbconn.cursor()
            cursor.execute("""
                UPDATE pf16_analysis_results SET
                    status = %s,
                    raw_response = %s,
                    personality_scores = %s,
                    composite_scores = %s,
                    overall_role_fit = %s,
                    analysis_confidence = %s,
                    error_message = %s,
                    completed_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (
                status,
                json.dumps(raw_response) if raw_response else None,
                json.dumps(personality_scores) if personality_scores else None,
                json.dumps(composite_scores) if composite_scores else None,
                overall_role_fit,
                analysis_confidence,
                error_message,
                analysis_id
            ))
            dbconn.commit()
            return True
    except Exception as e:
        print(f"Error updating 16PF analysis result: {str(e)}")
        return False


def get_16pf_analysis_by_play_id(play_id):
    """Get 16PF analysis result for a specific play session"""
    import json
    try:
        with ms.connect(host=host, user=user, password=password, database=database) as dbconn:
            cursor = dbconn.cursor(dictionary=True)
            cursor.execute("""
                SELECT * FROM pf16_analysis_results WHERE play_id = %s
            """, (play_id,))
            result = cursor.fetchone()
            if result:
                # Parse JSON fields
                if result.get('raw_response'):
                    result['raw_response'] = json.loads(result['raw_response'])
                if result.get('personality_scores'):
                    result['personality_scores'] = json.loads(result['personality_scores'])
                if result.get('composite_scores'):
                    result['composite_scores'] = json.loads(result['composite_scores'])
            return result
    except Exception as e:
        print(f"Error getting 16PF analysis: {str(e)}")
        return None


def get_16pf_config_for_roleplay(roleplay_id):
    """Get 16PF configuration for a roleplay"""
    try:
        with ms.connect(host=host, user=user, password=password, database=database) as dbconn:
            cursor = dbconn.cursor(dictionary=True)
            cursor.execute("""
                SELECT enable_16pf_analysis, pf16_analysis_source, 
                       pf16_user_age_required, pf16_user_gender_required,
                       pf16_default_age, pf16_send_audio_for_analysis
                FROM roleplay_config WHERE roleplay_id = %s
            """, (roleplay_id,))
            return cursor.fetchone()
    except Exception as e:
        print(f"Error getting 16PF config: {str(e)}")
        return None

