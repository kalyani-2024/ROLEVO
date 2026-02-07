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
import sys


from dotenv import load_dotenv

# Suppress pandas SQLAlchemy warnings for mysql.connector usage
warnings.filterwarnings('ignore', message='.*pandas only supports SQLAlchemy.*')

load_dotenv()

host = os.getenv('DB_HOST', 'localhost')
user = os.getenv('DB_USER', 'root')
password = os.getenv('DB_PASSWORD')
database = os.getenv('DB_NAME', 'roleplay')

def debug_log(msg):
    """Force output to stderr for debugging (bypasses silent_print)"""
    sys.stderr.write(f"[DEBUG] {msg}\n")
    sys.stderr.flush()

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

def create_or_update(id, name, person_name, scenario, roleplay_file_path, image_file_path, competency_file_path='', scenario_file_path='', logo_path='', config_data=None):
    """
    Create or update roleplay. If config_data is provided, also saves roleplay_config.
    Commits roleplay first, then config, to satisfy foreign key constraints.
    """
    dbconn = None
    cursor = None
    try:
        debug_log(f"🔧 create_or_update called: id={id}, name={name}, config_data={'provided' if config_data else 'None'}")
        dbconn = ms.connect(host=host, user=user, password=password, database=database)
        cursor = dbconn.cursor()

        query = "SELECT file_path, image_file_path, competency_file_path, scenario_file_path, logo_path FROM roleplay WHERE id = %s"
        roleplay_id = id
        cursor.execute(query, (roleplay_id,))
        result = cursor.fetchone()
        
        debug_log(f"🔧 Existing roleplay found: {result is not None}")

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
            debug_log(f"✅ UPDATE executed for roleplay {id}")
            dbconn.commit()  # Commit UPDATE
            debug_log(f"✅ UPDATE committed for roleplay {id}")
        else:
            # Insert new row
            # Generate alphanumeric ID if not provided
            if not id:
                id = generate_unique_roleplay_id()
            
            debug_log(f"🔧 Inserting new roleplay with id={id}")
            insert_query = (
                "INSERT INTO roleplay (id, name, person_name, scenario, file_path, image_file_path, competency_file_path, scenario_file_path, logo_path) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
            )
            cursor.execute(insert_query, (id, name, person_name, scenario, roleplay_file_path, image_file_path, competency_file_path, scenario_file_path, logo_path))
            debug_log(f"✅ INSERT executed for roleplay {id}")
        
        # If config_data provided, save config IN SAME TRANSACTION (FK checks disabled)
        if config_data:
            debug_log(f"🔧 Saving config in same transaction for roleplay {id}")
            _save_roleplay_config_internal(cursor, id, config_data)
            debug_log(f"✅ Config INSERT/UPDATE executed for roleplay {id}")
        
        # Commit everything together
        dbconn.commit()
        debug_log(f"✅ Transaction committed for roleplay {id}")
        
        # Verify config was saved by reading it back
        if config_data:
            cursor.execute("SELECT input_type, available_languages FROM roleplay_config WHERE roleplay_id = %s", (id,))
            verify = cursor.fetchone()
            if verify:
                debug_log(f"✅ Config verified: input_type={verify[0]}, languages={verify[1]}")
            else:
                debug_log(f"❌ WARNING: Config not found after commit for {id}!")
        
        return id

    except Exception as e:
        debug_log(f"❌ Error in create_or_update: {str(e)}")
        if dbconn:
            try:
                dbconn.rollback()
                debug_log(f"❌ Transaction rolled back")
            except:
                pass
        import traceback
        debug_log(f"❌ Traceback: {traceback.format_exc()}")
        print("Error in create_or_update:", str(e))
        traceback.print_exc()
        return None
    finally:
        if cursor:
            cursor.close()
        if dbconn:
            dbconn.close()

def delete_roleplay(id):
    try:
        with ms.connect(host=host, user=user, password=password, database=database) as dbconn:
            cursor = dbconn.cursor()

            # Delete related records in correct order to avoid foreign key constraint violations
            
            # Step 1: Get all play_ids for this roleplay
            cursor.execute("SELECT id FROM play WHERE roleplay_id = %s", (id,))
            play_ids = [row[0] for row in cursor.fetchall()]
            
            # Step 2: For each play, get chathistory_ids
            chathistory_ids = []
            for play_id in play_ids:
                cursor.execute("SELECT id FROM chathistory WHERE play_id = %s", (play_id,))
                chathistory_ids.extend([row[0] for row in cursor.fetchall()])
            
            # Step 3: Get scoremaster_ids for the chathistory records
            scoremaster_ids = []
            if chathistory_ids:
                placeholders = ','.join(['%s'] * len(chathistory_ids))
                cursor.execute(f"SELECT id FROM scoremaster WHERE chathistory_id IN ({placeholders})", chathistory_ids)
                scoremaster_ids = [row[0] for row in cursor.fetchall()]
            
            # Step 4: Delete scorebreakdown records (references scoremaster)
            if scoremaster_ids:
                placeholders = ','.join(['%s'] * len(scoremaster_ids))
                cursor.execute(f"DELETE FROM scorebreakdown WHERE scoremaster_id IN ({placeholders})", scoremaster_ids)
                print(f"   - Deleted {cursor.rowcount} scorebreakdown records")
            
            # Step 5: Delete scoremaster records (references chathistory)
            if chathistory_ids:
                placeholders = ','.join(['%s'] * len(chathistory_ids))
                cursor.execute(f"DELETE FROM scoremaster WHERE chathistory_id IN ({placeholders})", chathistory_ids)
                print(f"   - Deleted {cursor.rowcount} scoremaster records")
            
            # Step 6: Delete chathistory records
            if chathistory_ids:
                placeholders = ','.join(['%s'] * len(chathistory_ids))
                cursor.execute(f"DELETE FROM chathistory WHERE id IN ({placeholders})", chathistory_ids)
                print(f"   - Deleted {cursor.rowcount} chathistory records")
            
            # Step 7: Delete 16PF analysis results for this roleplay's plays
            if play_ids:
                placeholders = ','.join(['%s'] * len(play_ids))
                cursor.execute(f"DELETE FROM pf16_analysis_results WHERE play_id IN ({placeholders})", play_ids)
                print(f"   - Deleted {cursor.rowcount} 16PF analysis records")
            
            # Step 8: Delete play records
            cursor.execute("DELETE FROM play WHERE roleplay_id = %s", (id,))
            print(f"   - Deleted {cursor.rowcount} play records")
            
            # Step 9: Delete cluster associations
            cursor.execute("DELETE FROM cluster_roleplay WHERE roleplay_id = %s", (id,))
            print(f"   - Deleted {cursor.rowcount} cluster associations")
            
            # Step 10: Delete roleplay config
            cursor.execute("DELETE FROM roleplay_config WHERE roleplay_id = %s", (id,))
            print(f"   - Deleted {cursor.rowcount} roleplay configs")
            
            # Step 11: Delete roleplay overrides
            cursor.execute("DELETE FROM roleplayoverride WHERE roleplay_id = %s", (id,))
            print(f"   - Deleted {cursor.rowcount} roleplay overrides")
            
            # Step 12: Finally, delete the roleplay itself
            cursor.execute("DELETE FROM roleplay WHERE id = %s", (id,))
            print("   - Deleted roleplay")

            # Commit the transaction
            dbconn.commit()

            return True

    except Exception as e:
        print(f"Error deleting roleplay {id}: {str(e)}")
        import traceback
        traceback.print_exc()
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
            if result:
                debug_log(f"📖 get_roleplay({id}): found, id column value = {result[0]}")
            else:
                debug_log(f"📖 get_roleplay({id}): NOT found")
            return result
    except Exception as e:
        debug_log(f"❌ get_roleplay error: {str(e)}")
        return None

def get_roleplays():
    try:
        with ms.connect(host=host, user=user, password=password, database=database) as dbconn:
            cur = dbconn.cursor()
            # Order by creation date (latest first) for admin listing
            query = "SELECT * FROM roleplay ORDER BY created_at DESC"
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
                                
                                debug_log(f"Master file abbr_to_full_name mappings ({len(abbr_to_full_name)} total): {dict(list(abbr_to_full_name.items())[:15])}")
                    except Exception as e:
                        debug_log(f"Error loading master file: {e}")
                        import traceback
                        debug_log(f"Master file traceback: {traceback.format_exc()}")
                        pass  # Continue with empty dict
                    
                    try:
                        # Read max scores from Tags sheet and map abbreviations to full names
                        import pandas as pd
                        xls = pd.ExcelFile(excel_path)
                        tags_sheet = None
                        for sheet in xls.sheet_names:
                            if "tags" in sheet.lower():
                                tags_sheet = sheet
                                break
                        
                        debug_log(f"Tags sheet found: {tags_sheet}")
                        
                        if tags_sheet:
                            # Read the entire sheet without treating first row as header
                            tag_data = xls.parse(tags_sheet, header=None)
                            
                            # Find the row that contains "Competenc" and "max"
                            header_row_idx = None
                            for idx in range(len(tag_data)):
                                row_values = tag_data.iloc[idx].astype(str).str.lower().tolist()
                                has_competency = any('competenc' in str(v).lower() for v in row_values)
                                has_max_score = any('max' in str(v).lower() for v in row_values)
                                if has_competency and has_max_score:
                                    header_row_idx = idx
                                    break
                            
                            debug_log(f"Tags header row index: {header_row_idx}")
                            
                            if header_row_idx is not None:
                                # Re-parse with correct header row
                                tag_data = xls.parse(tags_sheet, header=header_row_idx)
                                debug_log(f"Tags columns: {list(tag_data.columns)}")
                                
                                # Build dictionary: abbreviation -> max_score, and full_name -> max_score
                                for idx, row in tag_data.iterrows():
                                    # Get Enabled value
                                    enabled = None
                                    for col in ['Enabled', 'enabled', tag_data.columns[2] if len(tag_data.columns) > 2 else None]:
                                        if col and col in tag_data.columns:
                                            enabled = row.get(col)
                                            if pd.notna(enabled):
                                                break
                                    
                                    # Get competency abbreviation
                                    comp_abbr = None
                                    for col in ['Competencies', 'Competency', 'competencies', 'competency', tag_data.columns[0]]:
                                        if col and col in tag_data.columns:
                                            comp_abbr = row.get(col)
                                            if pd.notna(comp_abbr):
                                                break
                                    
                                    # Get max score
                                    max_score = None
                                    for col in ['max scores', 'Max scores', 'Max Score', 'max score', tag_data.columns[1] if len(tag_data.columns) > 1 else None]:
                                        if col and col in tag_data.columns:
                                            max_score = row.get(col)
                                            if pd.notna(max_score):
                                                break
                                    
                                    # Only process if enabled = 'Y' or not specified
                                    enabled_ok = (enabled == 'Y' or enabled is None or pd.isna(enabled))
                                    
                                    if comp_abbr and pd.notna(max_score) and enabled_ok:
                                        comp_abbr_str = str(comp_abbr).strip()
                                        try:
                                            max_score_int = int(float(max_score))
                                            
                                            # Store with abbreviation (both original case and upper)
                                            max_scores_dict[comp_abbr_str] = max_score_int
                                            max_scores_dict[comp_abbr_str.upper()] = max_score_int
                                            max_scores_dict[comp_abbr_str.lower()] = max_score_int
                                            
                                            # Map to full name using abbr_to_full_name (from master file loaded earlier)
                                            full_name = abbr_to_full_name.get(comp_abbr_str.upper())
                                            if full_name:
                                                max_scores_dict[full_name] = max_score_int
                                                max_scores_dict[full_name.lower()] = max_score_int
                                                debug_log(f"Tags: '{comp_abbr_str}' -> full_name '{full_name}' max={max_score_int}")
                                            else:
                                                debug_log(f"Tags: '{comp_abbr_str}' max={max_score_int} (no full name mapping)")
                                        except (ValueError, TypeError) as e:
                                            debug_log(f"Error parsing max_score for {comp_abbr_str}: {e}")
                                            pass
                        
                        debug_log(f"max_scores_dict has {len(max_scores_dict)} entries")
                        debug_log(f"max_scores_dict keys (first 20): {list(max_scores_dict.keys())[:20]}")
                    except Exception as e:
                        debug_log(f"Error reading Tags sheet: {e}")
                        import traceback
                        debug_log(f"Tags sheet traceback: {traceback.format_exc()}")
                        pass  # Continue with empty dict

            cur.execute("select * from chathistory where play_id=%s order by id asc", (play_id,))
            df = cur.fetchall()
            
            debug_log(f"query_showreport: play_id={play_id}, chathistory rows found={len(df)}")
            
            if not df or len(df) == 0:
                debug_log(f"WARNING: No chathistory entries found for play_id={play_id}")
                return None
            
            results = []
            scoremaster_found_count = 0
            for row in df:
                chathistory_id = row[0]
                data = {}
                data["user"] = row[2]
                data["computer"] = row[3]

                cur.execute("select * from scoremaster where chathistory_id=%s", (chathistory_id,))
                df2 = cur.fetchall()
                
                if not df2:
                    debug_log(f"WARNING: No scoremaster entry for chathistory_id={chathistory_id}")
                    continue
                
                scoremaster_found_count += 1
                    
                scoremaster_data = df2[0]
                data["score"] = scoremaster_data[2]

                cur.execute("select * from scorebreakdown where scoremaster_id=%s", (scoremaster_data[0],))
                df3 = cur.fetchall()

                scoredata = []
                for row2 in df3:
                    # scorebreakdown columns: id(0), scoremaster_id(1), score_name(2), score(3)
                    # Add safety check for tuple length
                    if len(row2) >= 4:
                        scoredata.append({"name": row2[2], "score": row2[3]})
                    elif len(row2) >= 3:
                        # Fallback: might be (id, score_name, score) without scoremaster_id
                        scoredata.append({"name": row2[1], "score": row2[2]})
                    else:
                        debug_log(f"WARNING: scorebreakdown row has unexpected format: {row2}")
                data["competencies"] = scoredata

                results.append(data)

            debug_log(f"query_showreport: results count={len(results)}, scoremaster entries found={scoremaster_found_count}")
            
            if len(results) == 0:
                debug_log(f"ERROR: No results built - all chathistory entries missing scoremaster!")
                return None
            
            # Debug: show what competencies we have from database
            all_db_competencies = set()
            for entry in results:
                for score in entry["competencies"]:
                    all_db_competencies.add(str(score["name"]) if score["name"] is not None else "")
            debug_log(f"Database competencies: {list(all_db_competencies)}")
            debug_log(f"Tags sheet max_scores_dict keys: {[k for k in max_scores_dict.keys() if isinstance(k, str)][:20]}")  # First 20
            
            score_totals = {}
            for entry in results:
                for score in entry["competencies"]:
                    comp_name = str(score["name"]) if score["name"] is not None else ""
                    
                    # Convert score to integer (may be stored as string in DB)
                    try:
                        score_value = int(float(score["score"])) if score["score"] is not None else 0
                    except (ValueError, TypeError):
                        score_value = 0
                    
                    if not comp_name:
                        continue  # Skip empty competency names
                    
                    if comp_name in score_totals:
                        score_totals[comp_name]["score"] += score_value
                        # DON'T cap score - let it exceed max to detect "overused" competencies
                        # The report will show overused competencies with the balance scale
                    else:
                        # Get max score from Tags sheet - try multiple matching strategies
                        max_score_total = None
                        matched_key = None
                        
                        # Strategy 1: Exact match
                        if comp_name in max_scores_dict:
                            max_score_total = max_scores_dict[comp_name]
                            matched_key = comp_name
                            debug_log(f"MATCHED (exact): '{comp_name}' -> max={max_score_total}")
                        
                        # Strategy 2: Case-insensitive match
                        if max_score_total is None:
                            for key in max_scores_dict.keys():
                                if isinstance(key, str) and key.lower() == comp_name.lower():
                                    max_score_total = max_scores_dict[key]
                                    matched_key = key
                                    debug_log(f"MATCHED (case-insensitive): '{comp_name}' -> '{key}' max={max_score_total}")
                                    break
                        
                        # Strategy 3: Partial match - check if Tags key contains part of comp_name or vice versa
                        if max_score_total is None:
                            # Extract base competency name (remove "Level X" and common suffixes)
                            import re
                            comp_base = re.sub(r'\s*Level\s*\d+\s*', '', comp_name, flags=re.IGNORECASE).strip()
                            comp_base = comp_base.replace('-', '').replace('/', '').lower()
                            
                            for key in max_scores_dict.keys():
                                if not isinstance(key, str):
                                    continue  # Skip non-string keys
                                key_base = re.sub(r'\s*Level\s*\d+\s*', '', key, flags=re.IGNORECASE).strip()
                                key_base = key_base.replace('-', '').replace('/', '').lower()
                                
                                # Check for partial matches (e.g., "persuasion" matches "persuade")
                                if comp_base in key_base or key_base in comp_base:
                                    max_score_total = max_scores_dict[key]
                                    matched_key = key
                                    debug_log(f"MATCHED (partial): '{comp_name}' -> '{key}' max={max_score_total}")
                                    break
                        
                        # If no match found in Tags sheet, use default max score based on interactions count
                        # This ensures ALL competencies from the database appear in the report
                        if max_score_total is None:
                            # Calculate default max as 3 points per interaction (rough estimate)
                            default_max = len(results) * 3 if len(results) > 0 else 3
                            max_score_total = default_max
                            debug_log(f"NO MATCH for competency: '{comp_name}' - using default max={default_max}")
                        
                        score_totals[comp_name] = {"score": score_value, "total": max_score_total, "matched": True}

            debug_log(f"Final score_totals has {len(score_totals)} competencies")
            debug_log(f"competency_descriptions keys: {list(competency_descriptions.keys())}")
            
            # Final pass: DON'T cap scores - keep actual values to show overused
            processed_score_totals = []
            for key in score_totals:
                final_score_value = score_totals[key]["score"]
                max_allowed = score_totals[key]["total"]
                
                # Keep actual score even if it exceeds max - this shows "overused"
                # The report generator will handle displaying overused competencies
                
                # Get description from master file - try multiple matching strategies
                description = ''
                
                # Strategy 1: Exact match by key (competency name from DB)
                if key in competency_descriptions:
                    description = competency_descriptions[key]
                    debug_log(f"Description match (exact): '{key}' -> '{description[:50]}...'")
                
                # Strategy 2: Case-insensitive match
                if not description:
                    for desc_key, desc_val in competency_descriptions.items():
                        if desc_key.lower() == key.lower():
                            description = desc_val
                            debug_log(f"Description match (case-insensitive): '{key}' -> '{desc_key}' -> '{description[:50]}...'")
                            break
                
                # Strategy 3: Look up via abbreviation mapping - key might be an abbreviation
                if not description:
                    key_upper = key.upper().strip()
                    if key_upper in abbr_to_full_name:
                        full_name = abbr_to_full_name[key_upper]
                        if full_name in competency_descriptions:
                            description = competency_descriptions[full_name]
                            debug_log(f"Description match (via abbr): '{key}' -> '{full_name}' -> '{description[:50]}...'")
                
                # Strategy 4: Partial match - check if key contains or is contained in any description key
                if not description:
                    key_lower = key.lower().strip()
                    for desc_key, desc_val in competency_descriptions.items():
                        desc_key_lower = desc_key.lower().strip()
                        if key_lower in desc_key_lower or desc_key_lower in key_lower:
                            description = desc_val
                            debug_log(f"Description match (partial): '{key}' -> '{desc_key}' -> '{description[:50]}...'")
                            break
                
                if not description:
                    debug_log(f"No description found for: '{key}'")
                
                processed_score_totals.append({
                    "name": key, 
                    "score": final_score_value, 
                    "total_possible": max_allowed,
                    "description": description,
                    "overused": final_score_value > max_allowed  # Flag for overused
                })

            debug_log(f"processed_score_totals has {len(processed_score_totals)} entries")

            final_score = {"overall_score": {"score":0, "total":0}}
            for entry in results:
                final_score["overall_score"]["score"] += entry["score"]
                final_score["overall_score"]["total"] += 3

            debug_log(f"query_showreport SUCCESS: returning {len(results)} results, {len(processed_score_totals)} competencies")
        return results, processed_score_totals, final_score
    except Exception as e:
        import traceback
        debug_log(f"ERROR in query_showreport: {e}")
        debug_log(f"Traceback: {traceback.format_exc()}")
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
            debug_log("ERROR: No play_id in session for chat entry")
            raise ValueError("No active play session")
        
        play_id = session['play_id']
        debug_log(f"Creating chat entry: play_id={play_id}, user_text={user_text[:30] if user_text else 'None'}...")

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
        """, (play_id, user_text, response_text))
        
        conn.commit()
        chathistory_id = cur.lastrowid
        debug_log(f"Chat entry created: chathistory_id={chathistory_id}")
        
        cur.close()
        conn.close()
        return chathistory_id

    except Exception as e:
        debug_log(f"ERROR creating chat entry: {str(e)}")
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


def query_get_play_cumulative_score(play_id):
    """
    Get the cumulative score (sum and count) for a play session.
    Returns a dict with 'total_score', 'interaction_count', and 'average_score'.
    The average_score is used to determine computer response level on timeout.
    """
    try:
        with ms.connect(host=host, user=user, password=password, database=database) as dbconn:
            cursor = dbconn.cursor()
            
            # Get all scores from scoremaster for this play session
            query = """
                SELECT SUM(sm.overall_score) as total_score, COUNT(sm.id) as interaction_count
                FROM chathistory ch
                JOIN scoremaster sm ON ch.id = sm.chathistory_id
                WHERE ch.play_id = %s
            """
            cursor.execute(query, (play_id,))
            result = cursor.fetchone()
            
            if result and result[0] is not None:
                total_score = int(result[0])
                interaction_count = int(result[1])
                average_score = total_score / interaction_count if interaction_count > 0 else 0
                return {
                    'total_score': total_score,
                    'interaction_count': interaction_count,
                    'average_score': average_score
                }
            
            return {'total_score': 0, 'interaction_count': 0, 'average_score': 0}
    except Exception as e:
        print(f"Error getting cumulative score: {e}")
        return {'total_score': 0, 'interaction_count': 0, 'average_score': 0}


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

def _save_roleplay_config_internal(cursor, roleplay_id, config_data):
    """Internal helper: Save roleplay config using existing cursor/transaction"""
    # Temporarily disable foreign key checks to handle PythonAnywhere replication lag
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
    
    try:
        # Check if config exists
        cursor.execute("SELECT id, ideal_video_path FROM roleplay_config WHERE roleplay_id = %s", (roleplay_id,))
        existing = cursor.fetchone()
        
        # If ideal_video_path is None, preserve existing path
        ideal_video_path = config_data.get('ideal_video_path')
        if ideal_video_path is None and existing:
            ideal_video_path = existing[1] if existing[1] else ''
        elif ideal_video_path is None:
            ideal_video_path = ''
        
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
                ideal_video_path,
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
                ideal_video_path,
                config_data['voice_assessment_enabled'],
                config_data.get('difficulty_level', 'easy'),
                config_data.get('enable_16pf_analysis', False),
                config_data.get('pf16_analysis_source', 'none'),
                config_data.get('pf16_user_age_required', True),
                config_data.get('pf16_user_gender_required', True),
                config_data.get('pf16_default_age', 30),
                config_data.get('pf16_send_audio_for_analysis', True)
            ))
    finally:
        # Re-enable foreign key checks
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")

def create_or_update_roleplay_config(roleplay_id, config_data):
    """Create or update roleplay configuration"""
    dbconn = None
    cursor = None
    try:
        debug_log(f"🔧 Starting config save for roleplay_id={roleplay_id}")
        debug_log(f"🔧 Config data keys: {list(config_data.keys())}")
        
        dbconn = ms.connect(host=host, user=user, password=password, database=database)
        cursor = dbconn.cursor()
        
        # Verify parent roleplay exists (with retry for PythonAnywhere replication lag)
        max_retries = 10
        retry_delay = 0.5  # 500ms - PythonAnywhere has significant replication lag
        roleplay_exists = False
        
        for attempt in range(max_retries):
            cursor.execute("SELECT id FROM roleplay WHERE id = %s", (roleplay_id,))
            if cursor.fetchone():
                roleplay_exists = True
                debug_log(f"✅ Parent roleplay {roleplay_id} found (attempt {attempt + 1})")
                break
            else:
                if attempt < max_retries - 1:
                    debug_log(f"⏳ Parent roleplay not found yet, waiting {retry_delay}s... (attempt {attempt + 1}/{max_retries})")
                    import time
                    time.sleep(retry_delay)
                else:
                    debug_log(f"❌ Parent roleplay {roleplay_id} not found after {max_retries} attempts ({max_retries * retry_delay}s total)")
        
        if not roleplay_exists:
            debug_log(f"❌ Cannot save config: roleplay {roleplay_id} does not exist")
            return False
        
        # Check if config exists
        cursor.execute("SELECT id, ideal_video_path FROM roleplay_config WHERE roleplay_id = %s", (roleplay_id,))
        existing = cursor.fetchone()
        debug_log(f"🔧 Existing config found: {existing is not None}")
        
        # If ideal_video_path is None, preserve existing path (no new video uploaded)
        ideal_video_path = config_data.get('ideal_video_path')
        if ideal_video_path is None and existing:
            ideal_video_path = existing[1] if existing[1] else ''
        elif ideal_video_path is None:
            ideal_video_path = ''
        
        # Enforce: 16PF analysis can only be enabled for audio input type
        if config_data.get('input_type') != 'audio':
            config_data['enable_16pf_analysis'] = False
            config_data['pf16_analysis_source'] = 'none'

        if existing:
            # Update existing configuration
            debug_log(f"🔧 Updating existing config (id={existing[0]})")
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
                ideal_video_path,
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
            debug_log(f"✅ UPDATE executed, rows affected: {cursor.rowcount}")
        else:
            # Create new configuration
            debug_log(f"🔧 Creating new config entry")
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
                ideal_video_path,
                config_data['voice_assessment_enabled'],
                config_data.get('difficulty_level', 'easy'),
                config_data.get('enable_16pf_analysis', False),
                config_data.get('pf16_analysis_source', 'none'),
                config_data.get('pf16_user_age_required', True),
                config_data.get('pf16_user_gender_required', True),
                config_data.get('pf16_default_age', 30),
                config_data.get('pf16_send_audio_for_analysis', True)
            ))
            debug_log(f"✅ INSERT executed, last insert id: {cursor.lastrowid}")
        
        # Explicit commit
        dbconn.commit()
        debug_log(f"✅ Database commit successful for roleplay_id={roleplay_id}")
        
        # Verify the save by reading back
        cursor.execute("SELECT input_type, available_languages FROM roleplay_config WHERE roleplay_id = %s", (roleplay_id,))
        verify = cursor.fetchone()
        if verify:
            debug_log(f"✅ Verification: config exists with input_type={verify[0]}, languages={verify[1]}")
        else:
            debug_log(f"❌ WARNING: Config not found after save!")
        
        return True
    except Exception as e:
        debug_log(f"❌ Error creating/updating roleplay config: {str(e)}")
        import traceback
        debug_log(f"❌ Traceback: {traceback.format_exc()}")
        if dbconn:
            try:
                dbconn.rollback()
                debug_log(f"❌ Transaction rolled back")
            except:
                pass
        return False
    finally:
        if cursor:
            cursor.close()
        if dbconn:
            dbconn.close()

def get_roleplay_config(roleplay_id):
    """Get roleplay configuration"""
    try:
        with ms.connect(host=host, user=user, password=password, database=database) as dbconn:
            cursor = dbconn.cursor()
            cursor.execute("SELECT * FROM roleplay_config WHERE roleplay_id = %s", (roleplay_id,))
            result = cursor.fetchone()
            debug_log(f"📖 get_roleplay_config({roleplay_id}): found={result is not None}")
            if result:
                debug_log(f"📖 Config: input_type={result[1] if len(result) > 1 else 'N/A'}")
            return result
    except Exception as e:
        debug_log(f"❌ Error getting roleplay config: {str(e)}")
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
    """Get specific cluster by internal id (use get_cluster_by_id_or_external for id or external cluster_id)."""
    try:
        with ms.connect(host=host, user=user, password=password, database=database) as dbconn:
            cursor = dbconn.cursor()
            cursor.execute("SELECT * FROM roleplay_cluster WHERE id = %s", (cluster_id,))
            return cursor.fetchone()
    except Exception as e:
        print(f"Error getting cluster: {str(e)}")
        return None


def get_cluster_by_id_or_external(id_or_external):
    """Get cluster by internal id (int) or external cluster_id (string)."""
    try:
        with ms.connect(host=host, user=user, password=password, database=database) as dbconn:
            cursor = dbconn.cursor()
            cursor.execute(
                "SELECT * FROM roleplay_cluster WHERE id = %s OR cluster_id = %s",
                (id_or_external, str(id_or_external)),
            )
            return cursor.fetchone()
    except Exception as e:
        print(f"Error getting cluster by id or external: {str(e)}")
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
                SELECT u.id, u.email, u.is_admin
                FROM user u
                INNER JOIN user_cluster uc ON u.id = uc.user_id
                WHERE uc.cluster_id = %s
                ORDER BY u.email
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
            result = cursor.fetchone()
            if result is None:
                print(f"[16PF Config] No roleplay_config entry found for roleplay_id={roleplay_id}")
                # Check if roleplay_config table has ANY entries for this roleplay
                cursor.execute("SELECT COUNT(*) as cnt FROM roleplay_config WHERE roleplay_id = %s", (roleplay_id,))
                count_result = cursor.fetchone()
                print(f"[16PF Config] Count check: {count_result}")
            return result
    except Exception as e:
        print(f"Error getting 16PF config: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

