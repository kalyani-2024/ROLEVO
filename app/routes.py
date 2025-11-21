from flask import render_template, request, session, redirect, url_for, flash, abort, send_file, jsonify
import mysql.connector
from app import app
from app.forms import PostForm
import openai
import reader.master #abstract this
import reader.excel
import interface.openai
import interface.interact
import os
import json
import threading
from app.queries import get_roleplay_file_path, old_query_showreport, get_play_info, query_create_chat_entry, query_create_score_master, query_create_score_breakdown, query_update, query_showreport, create_or_update, get_roleplays, get_roleplay, delete_roleplay, create_or_update_roleplay_config, get_roleplay_config, get_roleplay_with_config, create_cluster, update_cluster, get_clusters, get_cluster, add_roleplay_to_cluster, remove_roleplay_from_cluster, get_cluster_roleplays, delete_cluster, get_all_users, get_user, assign_cluster_to_user, remove_cluster_from_user, get_user_clusters, get_cluster_users, get_user_id, create_user_account, get_user_by_email, create_user
from gtts import gTTS
from deep_translator import GoogleTranslator
from dotenv import load_dotenv, find_dotenv
import uuid
import time
import requests
from werkzeug.security import generate_password_hash
from functools import wraps
from app.report_generator import generate_roleplay_report
from app.email_service import send_report_email

load_dotenv(find_dotenv())
openai.api_key = os.getenv('OPENAI_API_KEY')

# Admin authentication decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('is_admin') != 1:
            flash('Admin access required. Please login.')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# Load competency descriptions from configured upload path. If the file is missing,
# fall back to an empty list so the app doesn't crash with FileNotFoundError.
comp_filename = 'Competency descriptions.xlsx'
comp_dir = app.config.get('UPLOAD_PATH_COMP', os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'master'))
comp_path = os.path.join(comp_dir, comp_filename)
if not os.path.exists(comp_path):
    print(f"Warning: competency descriptions file not found at {comp_path}. Using empty competency list.")
    competency_descriptions = []
else:
    master_obj = reader.master.MasterLoader(comp_path)
    competency_descriptions = master_obj.get_competencies_as_list()

def cumul_score(roleplay_id):
    play_data_df = old_query_showreport(roleplay_id)

    if play_data_df is None:
        return {}

    results = []

    for row in play_data_df.itertuples():
        if not results or results[-1]["user"] != row.user_text:
            results.append({
                "user": row.user_text,
                "comp": row.response_text,
                "scores": [{"name": row.score_name, "score": row.score}]
            })
        else:
            results[-1]["scores"].append({"name": row.score_name, "score": row.score})

        results[-1]["scores"].append({"name": "Final Score", "score": row.overall_score})

    # Calculate score totals
    score_totals = {}
    for entry in results:
        for score in entry["scores"]:
            if score["name"] in score_totals:
                score_totals[score["name"]]["score"] += score["score"]
                score_totals[score["name"]]["total"] += 3
            else:
                score_totals[score["name"]] = {"score": score["score"], "total": 3}
    if "Final Score" in score_totals:
        score_totals.pop("Final Score")
    return score_totals

import json
import datetime

# Translation helper function
def translate_text(text, target_language='English'):
    """
    Translate text to target language using Google Translator.
    Returns original text if target is English or if translation fails.
    """
    if not text or target_language == 'English':
        return text
    
    # Language code mapping for Google Translator
    language_codes = {
        'Hindi': 'hi',
        'Tamil': 'ta',
        'Telugu': 'te',
        'Kannada': 'kn',
        'Marathi': 'mr',
        'Bengali': 'bn',
        'Malayalam': 'ml',
        'French': 'fr',
        'Arabic': 'ar',
        'Gujarati': 'gu',
        'English': 'en'
    }
    
    target_code = language_codes.get(target_language, 'en')
    
    try:
        translator = GoogleTranslator(source='auto', target=target_code)
        translated = translator.translate(text)
        return translated
    except Exception as e:
        print(f"Translation error: {e}")
        return text  # Return original text if translation fails

# Utility: resolve a stored file path that may point to an old absolute location.
def resolve_file_path(db_path, upload_dirs=None):
    """Return an existing, absolute file path for db_path.

    Strategy:
    - If db_path exists, return its absolute path.
    - Otherwise, look for the file basename inside configured upload dirs
      (recursively). If found, return that path.
    - As a last resort, search the project's data folder recursively.
    - If nothing is found, return the original db_path (caller can detect missing file).
    """
    if not db_path:
        return ''
    try:
        if os.path.exists(db_path):
            return os.path.abspath(db_path)
    except Exception:
        # In case db_path is malformed
        pass

    basename = os.path.basename(db_path)
    # Build search directories list
    dirs = []
    if upload_dirs:
        dirs.extend(upload_dirs)
    # Fallback to common upload config paths
    dirs.extend([
        app.config.get('UPLOAD_PATH_ROLEPLAY'),
        app.config.get('UPLOAD_PATH_IMAGES'),
        app.config.get('UPLOAD_PATH_COMP')
    ])

    # Search each dir for the basename
    for d in dirs:
        if not d:
            continue
        candidate = os.path.join(d, basename)
        if os.path.exists(candidate):
            print(f"Resolved {db_path} -> {candidate}")
            return os.path.abspath(candidate)
        # recursive search
        if os.path.isdir(d):
            for root, _, files in os.walk(d):
                if basename in files:
                    found = os.path.join(root, basename)
                    print(f"Resolved {db_path} -> {found}")
                    return os.path.abspath(found)

    # Last resort: search project data folder
    project_data = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
    if os.path.isdir(project_data):
        for root, _, files in os.walk(project_data):
            if basename in files:
                found = os.path.join(root, basename)
                print(f"Resolved {db_path} -> {found}")
                return os.path.abspath(found)

    print(f"Warning: could not resolve file {db_path}; returning original path")
    return db_path

def serialize_datetime(obj):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    raise TypeError("Type not serializable")

def post_attempt_data(play_id):
    final_json = {}
    play_info = get_play_info(play_id)
    
    # Use session user_id as fallback if play record has NULL user_id
    user_id_from_play = play_info[2] if play_info else None
    user_id = user_id_from_play if user_id_from_play is not None else session.get('user_id')
    
    print(f"DEBUG post_attempt_data: play_id={play_id}, user_id from play={user_id_from_play}, user_id from session={session.get('user_id')}, final user_id={user_id}")
    
    final_json["start_time"] = play_info[1]
    final_json["user_id"] = user_id
    final_json["roleplay_id"] = play_info[3]

    report = query_showreport(play_id)

    final_json["conversation"] = report[0]
    final_json["competencies"] = report[1]
    final_json["overall_score"] = report[2]["overall_score"]

    final_json = json.loads(json.dumps(final_json, default=serialize_datetime))

    print(final_json, flush=True)

    post_url = "http://codrive.sgate.in/api/web/v1/coursejsons/data"
    r = requests.post(post_url, json=final_json)
    if not r.ok:
        #raise Exception("Error in posting data")
        flash("Failed to return data to Trajectorie")
    else:
        res = r.json()
        if not res["success"]:
            flash("Failed to return data to Trajectorie - something went wrong")
    
    # Generate and send report to user after scoring
    try:
        import threading
        # Run report generation in background thread to avoid blocking
        # Pass user_id explicitly as it might not be in play record
        thread = threading.Thread(target=generate_and_send_report_async, args=(play_id, user_id))
        thread.daemon = True
        thread.start()
        print(f"Started background report generation for play_id {play_id}, user_id {user_id}")
    except Exception as e:
        print(f"Error starting report generation thread: {str(e)}")

def create_chat_entry(user_text, response_text):
    chathistory_id = query_create_chat_entry(user_text, response_text)
    return chathistory_id

def create_score_master(chathistory_id, overall_score):
    scoremaster_id = query_create_score_master(chathistory_id, overall_score)
    return scoremaster_id

def create_score_breakdown(scoremaster_id, score_name, score):
    query_create_score_breakdown(scoremaster_id, score_name, score)

@app.route("/make_audio/", methods=["GET"])
def make_audio():
    try:
        text = request.args.get('text', '')
        if not text:
            return "No text provided", 400

        # Create cache directory
        cache_dir = os.path.join(app.root_path, 'static', 'audio_cache')
        os.makedirs(cache_dir, exist_ok=True)
        
        # Get selected language from session, default to English
        selected_language = session.get('selected_language', 'English')
        
        # Map language names to gTTS language codes
        language_map = {
            'English': 'en',
            'Hindi': 'hi',
            'Tamil': 'ta',
            'Telugu': 'te',
            'Kannada': 'kn',
            'Marathi': 'mr',
            'Bengali': 'bn',
            'Malayalam': 'ml',
            'French': 'fr',
            'Arabic': 'ar',
            'Gujarati': 'gu'
        }
        
        lang_code = language_map.get(selected_language, 'en')
        
        # Create unique filename based on text content and language
        filename = f'speech_{hash(text)}_{lang_code}.mp3'
        filepath = os.path.join(cache_dir, filename)
        
        # Check if audio file already exists in cache
        if not os.path.exists(filepath):
            try:
                tts = gTTS(text=text, lang=lang_code, slow=False)
                tts.save(filepath)
            except Exception as e:
                print(f"TTS Error: {str(e)}")
                return str(e), 500
        
        # Return cached file
        return send_file(
            filepath,
            mimetype="audio/mpeg",
            conditional=True,
            etag=True
        )
        
    except Exception as e:
        print(f"Audio generation error: {str(e)}")
        return str(e), 500



@app.route('/')
@app.route('/index')
def index():
    # If user is logged in, redirect to their dashboard
    if 'user_id' in session:
        user_id = session['user_id']
        # Get user's clusters
        user_clusters = get_user_clusters(user_id)
        if user_clusters and len(user_clusters) > 0:
            # Redirect to first cluster
            return redirect(url_for('user_cluster_view', user_id=user_id, cluster_id=user_clusters[0][0]))
        else:
            # No clusters assigned
            return redirect(url_for('user_dashboard', user_id=user_id))
    # Not logged in - redirect to login
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validation
        if not email or not password or not confirm_password:
            flash('All fields are required')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('Passwords do not match')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters')
            return render_template('register.html')
        
        # Create user
        user_id, message = create_user_account(email, password)
        
        if user_id:
            flash('Registration successful! Please login.')
            return redirect(url_for('login'))
        else:
            flash(f'Registration failed: {message}')
            return render_template('register.html')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            flash('Email and password are required')
            return render_template('login.html')
        
        # Authenticate user
        user = get_user_id(email, password)
        
        if user:
            # Set session
            session['user_id'] = user['id']
            session['is_admin'] = user['is_admin']
            
            # Redirect based on role
            if user['is_admin'] == 1:
                return redirect(url_for('admin'))
            else:
                # Redirect to user dashboard
                return redirect(url_for('index'))
        else:
            flash('Invalid email or password')
            return render_template('login.html')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """User logout"""
    session.clear()
    flash('You have been logged out')
    return redirect(url_for('login'))


@app.route('/download/scenario/<path:filename>')
def download_scenario_file(filename):
    """Download scenario file"""
    try:
        # Scenario files are stored in the images folder
        file_path = os.path.join(app.config['UPLOAD_PATH_IMAGES'], filename)
        
        if not os.path.exists(file_path):
            flash('Scenario file not found')
            return redirect(url_for('index'))
        
        # Get the original filename without the timestamp prefix
        original_filename = filename
        if '_' in filename:
            parts = filename.split('_', 2)  # Split on first 2 underscores (ID_timestamp_originalname)
            if len(parts) == 3:
                original_filename = parts[2]
        
        return send_file(file_path, as_attachment=True, download_name=original_filename)
    except Exception as e:
        print(f"Error downloading scenario file: {str(e)}")
        flash('Error downloading file')
        return redirect(url_for('index'))


@app.route("/launch/<int:user_id>/<path:roleplay_id>", methods=['GET', 'POST'])
def launch(user_id, roleplay_id):
    try:
        print(f"========================================")
        print(f"LAUNCH ROUTE CALLED!")
        print(f"User ID: {user_id} (type: {type(user_id)})")
        print(f"Roleplay ID: {roleplay_id} (type: {type(roleplay_id)})")
        print(f"Request method: {request.method}")
        print(f"========================================")
        print(f"Starting launch for user {user_id}, roleplay {roleplay_id}")
        
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME', 'roleplay')
        )
        cur = conn.cursor()

        # Get roleplay data
        cur.execute("""
            SELECT file_path, scenario, image_file_path 
            FROM roleplay 
            WHERE id = %s
        """, (roleplay_id,))
        
        roleplay_data = cur.fetchone()
        if not roleplay_data:
            print(f"No roleplay found with id {roleplay_id}")
            return render_template('404.html', title='Roleplay Not Found')

        # Get cluster_id and language from request args
        cluster_id = request.args.get('cluster_id', type=int)
        selected_language = request.args.get('language', 'English')  # Default to English

        print(f"Cluster ID from request.args: {cluster_id}")
        
        # If cluster_id is not in URL, try to get it from user_cluster table
        if cluster_id is None:
            print(f"No cluster_id in URL, querying user_cluster table for user_id={user_id}")
            cur.execute("""
                SELECT cluster_id FROM user_cluster 
                WHERE user_id = %s 
                LIMIT 1
            """, (user_id,))
            result = cur.fetchone()
            if result:
                cluster_id = result[0]
                print(f"Found cluster_id from user_cluster: {cluster_id}")
            else:
                print(f"No cluster found for user {user_id}")

        excel_path = resolve_file_path(roleplay_data[0], [app.config.get('UPLOAD_PATH_ROLEPLAY')])
        image_excel_path = resolve_file_path(roleplay_data[2], [app.config.get('UPLOAD_PATH_IMAGES')])

        print(f"Excel path: {excel_path}")
        print(f"Image Excel path: {image_excel_path}")
        print(f"Selected language: {selected_language}")

        # Get roleplay configuration for voice settings
        roleplay_config = get_roleplay_with_config(roleplay_id)
        input_type = 'audio'  # Always enable audio for scenario reading
        available_languages = 'English'  # Default
        max_interaction_time = 300  # Default 5 minutes
        max_total_time = 1800  # Default 30 minutes
        
        if roleplay_config and len(roleplay_config) > 10:
            # Index 10 is input_type from the query in get_roleplay_with_config
            # Always use 'audio' to ensure scenario is read out loud
            input_type = 'audio'
            # Index 12 is available_languages
            available_languages = roleplay_config[12] if roleplay_config[12] else 'English'
            # Index 13 is max_interaction_time
            max_interaction_time = roleplay_config[13] if roleplay_config[13] else 300
            # Index 14 is max_total_time
            max_total_time = roleplay_config[14] if roleplay_config[14] else 1800
        
        print(f"Input type: {input_type}")
        print(f"Available languages: {available_languages}")
        print(f"Max interaction time: {max_interaction_time} seconds")
        print(f"Max total time: {max_total_time} seconds")

        # Initialize session
        session.clear()
        session.update({
            'user_id': user_id,
            'roleplay_id': roleplay_id,
            'cluster_id': cluster_id,  # Store cluster_id in session
            'selected_language': selected_language,  # Store selected language
            'input_type': input_type,  # Store input type (audio or text)
            'available_languages': available_languages,  # Store available languages
            'max_interaction_time': max_interaction_time,  # Store max interaction time
            'max_total_time': max_total_time,  # Store max total time
            'interaction_number': 1,
            'image_interaction_number': 1,
            'exr_param0': excel_path,
            'exr_param2': image_excel_path,
            'roleplay_start_time': time.time()  # Store start time for total timer
        })

        # Create play record
        if cluster_id:
            cur.execute("""
                INSERT INTO play (user_id, roleplay_id, cluster_id, start_time) 
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
            """, (user_id, roleplay_id, cluster_id))
        else:
            cur.execute("""
                INSERT INTO play (user_id, roleplay_id, start_time) 
                VALUES (%s, %s, CURRENT_TIMESTAMP)
            """, (user_id, roleplay_id))
            
        conn.commit()
        session['play_id'] = cur.lastrowid

        cur.close()
        conn.close()

        # Initialize reader
        try:
            reader_obj = reader.excel.ExcelReader(
                excel_path,
                competency_descriptions,
                image_excel_path
            )
        except Exception as e:
            print(f"Error initializing Excel reader: {str(e)}")
            return render_template('500.html'), 500

        return redirect(url_for('chatbot', 
                              roleplay_id=session['roleplay_id'],
                              interaction_num=session['interaction_number']))

    except Exception as e:
        print(f"Launch error: {str(e)}")
        if 'conn' in locals():
            cur.close()
            conn.close()
        return render_template('500.html'), 500
    try:
        print(f"Starting launch for user {user_id}, roleplay {roleplay_id}")
        
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME', 'roleplay')
        )
        cur = conn.cursor()

        # Get roleplay data
        cur.execute("""
            SELECT file_path, scenario, image_file_path 
            FROM roleplay 
            WHERE id = %s
        """, (roleplay_id,))
        
        roleplay_data = cur.fetchone()
        if not roleplay_data:
            print(f"No roleplay found with id {roleplay_id}")
            return render_template('404.html', title='Roleplay Not Found')

        # Resolve file paths robustly. If the DB holds an old absolute path
        # (e.g. from Downloads) it may not exist anymore after moving files.
        # Use resolve_file_path() to find the file in the project's upload/data directories.
        excel_path = resolve_file_path(roleplay_data[0], [app.config.get('UPLOAD_PATH_ROLEPLAY')])
        image_excel_path = resolve_file_path(roleplay_data[2], [app.config.get('UPLOAD_PATH_IMAGES')])  # This is the Excel file containing image paths

        # Debug paths
        print(f"Excel path: {excel_path}")
        print(f"Image Excel path: {image_excel_path}")

        # Initialize session
        session.clear()
        session.update({
            'user_id': user_id,
            'roleplay_id': roleplay_id,
            'interaction_number': 1,
            'image_interaction_number': 1,
            'exr_param0': excel_path,
            'exr_param2': image_excel_path  # Changed from scenario to image_excel_path
        })

        # Create play record
        cur.execute("""
            INSERT INTO play (user_id, roleplay_id, start_time) 
            VALUES (%s, %s, CURRENT_TIMESTAMP)
        """, (user_id, roleplay_id))
        conn.commit()
        session['play_id'] = cur.lastrowid

        cur.close()
        conn.close()

        # Initialize reader with correct paths
        try:
            reader_obj = reader.excel.ExcelReader(
                excel_path,  # Main roleplay Excel file
                competency_descriptions,  # Competency descriptions
                image_excel_path  # Excel file containing image paths
            )
        except Exception as e:
            print(f"Error initializing Excel reader: {str(e)}")
            return render_template('500.html'), 500

        return redirect(url_for('chatbot', 
                              roleplay_id=session['roleplay_id'],
                              interaction_num=session['interaction_number']))

    except Exception as e:
        print(f"Launch error: {str(e)}")
        if 'conn' in locals():
            cur.close()
            conn.close()
        return render_template('500.html'), 500

@app.route("/chatbot/<path:roleplay_id>/<int:interaction_num>", methods=['GET', 'POST'])

def chatbot(roleplay_id, interaction_num):
    reader_obj = reader.excel.ExcelReader(session["exr_param0"], competency_descriptions, session["exr_param2"])
    interactor_obj = interface.interact.LLMInteractor(openai.api_key, reader_obj.get_system_prompt(), session['roleplay_id'])
    ai_obj = interface.openai.Conversation(reader_obj, interactor_obj)

    if roleplay_id == session['roleplay_id'] and interaction_num == session['interaction_number'] and session['user_id']:
        form = PostForm()
        resp = False
        if form.validate_on_submit():
            session['user_input'] = form.post.data.strip()
            return redirect(url_for('process_response'))

        context = {}
        context["scenario"] = reader_obj.get_system_prompt()
        context["image"] = reader_obj.get_system_prompt_image()
        context["cumul_score"] = cumul_score(roleplay_id)
        
        # Get cluster type from database - ALWAYS fetch fresh, don't cache
        cluster_type = 'training'  # Default
        cluster_id = session.get('cluster_id')
        user_id = session.get('user_id')
        
        print(f"DEBUG CLUSTER TYPE: user_id={user_id}, cluster_id from session={cluster_id}")
        
        # Always fetch fresh cluster type from database to avoid stale cached data
        if cluster_id:
            try:
                conn = mysql.connector.connect(
                    host=os.getenv('DB_HOST', 'localhost'),
                    user=os.getenv('DB_USER', 'root'),
                    password=os.getenv('DB_PASSWORD'),
                    database=os.getenv('DB_NAME', 'roleplay')
                )
                cur = conn.cursor()
                cur.execute("SELECT type FROM roleplay_cluster WHERE id = %s", (cluster_id,))
                result = cur.fetchone()
                if result:
                    cluster_type = result[0]
                    print(f"DEBUG: Fetched cluster type from roleplay_cluster: cluster_id={cluster_id}, type={cluster_type}")
                else:
                    print(f"DEBUG: No cluster found with id {cluster_id}")
                cur.close()
                conn.close()
            except Exception as e:
                print(f"Error fetching cluster type: {e}")
                import traceback
                traceback.print_exc()
        
        # If no cluster_id in session, try to get it from user_cluster table
        elif user_id:
            try:
                conn = mysql.connector.connect(
                    host=os.getenv('DB_HOST', 'localhost'),
                    user=os.getenv('DB_USER', 'root'),
                    password=os.getenv('DB_PASSWORD'),
                    database=os.getenv('DB_NAME', 'roleplay')
                )
                cur = conn.cursor()
                # Get the cluster that contains this roleplay for this user
                cur.execute("""
                    SELECT uc.cluster_id, rc.type
                    FROM user_cluster uc
                    JOIN roleplay_cluster rc ON uc.cluster_id = rc.id
                    JOIN cluster_roleplay cr ON rc.id = cr.cluster_id
                    WHERE uc.user_id = %s AND cr.roleplay_id = %s
                    LIMIT 1
                """, (user_id, roleplay_id))
                result = cur.fetchone()
                if result:
                    cluster_id = result[0]
                    cluster_type = result[1]
                    session['cluster_id'] = cluster_id  # Store in session for next time
                    print(f"DEBUG: Found cluster from user_cluster: cluster_id={cluster_id}, type={cluster_type}")
                else:
                    print(f"DEBUG: No cluster found for user {user_id} and roleplay {roleplay_id}")
                cur.close()
                conn.close()
            except Exception as e:
                print(f"Error querying user_cluster: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"DEBUG: Final cluster_type being sent to template: '{cluster_type}'")
        context["cluster_type"] = cluster_type
        
        # Get selected language for translation
        selected_language = session.get('selected_language', 'English')
        
        # Translate scenario if not in English
        if selected_language != 'English':
            context["scenario"] = translate_text(context["scenario"], selected_language)
        
        # Calculate elapsed time for total timer
        if 'roleplay_start_time' in session:
            elapsed_seconds = int(time.time() - session['roleplay_start_time'])
            context["elapsed_time"] = elapsed_seconds
        else:
            context["elapsed_time"] = 0

        if 'comp_dialogue' in session:
            comp_dialogue = session["comp_dialogue"]
            # Translate AI dialogue if not in English
            if selected_language != 'English':
                comp_dialogue = translate_text(comp_dialogue, selected_language)
            context["comp_dialogue"] = comp_dialogue
            context["last_round_result"] = session["last_round_result"]
            context["score"] = session["score"]
            context["image"] = reader_obj.get_images(session['image_interaction_number'])["images"][context["score"]-1]

        context["data"] = reader_obj.get_interaction(session['interaction_number'])
        if context["data"] == False:
            # Post attempt data to external API
            post_attempt_data(session['play_id'])
            
            # Update play status to completed in database
            try:
                conn = mysql.connector.connect(
                    host=os.getenv('DB_HOST', 'localhost'),
                    user=os.getenv('DB_USER', 'root'),
                    password=os.getenv('DB_PASSWORD'),
                    database=os.getenv('DB_NAME', 'roleplay')
                )
                cur = conn.cursor()
                cur.execute("""
                    UPDATE play 
                    SET status = 'completed', end_time = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (session['play_id'],))
                conn.commit()
                cur.close()
                conn.close()
                print(f"Updated play {session['play_id']} status to 'completed'")
            except Exception as e:
                print(f"Error updating play status: {str(e)}")
            
            # NEW: Redirect to completion page instead of showing inline
            user_id = session.get('user_id')
            
            # Ensure cluster_id is available
            if 'cluster_id' in session and session['cluster_id'] is not None:
                cluster_id = session['cluster_id']
            else:
                print("WARNING: cluster_id not in session, attempting to find from database")
                # Query database to find cluster_id for this user and roleplay
                try:
                    conn = mysql.connector.connect(
                        host=os.getenv('DB_HOST', 'localhost'),
                        user=os.getenv('DB_USER', 'root'),
                        password=os.getenv('DB_PASSWORD'),
                        database=os.getenv('DB_NAME', 'roleplay')
                    )
                    cur = conn.cursor()
                    cur.execute("""
                        SELECT cluster_id FROM user_cluster 
                        WHERE user_id = %s 
                        LIMIT 1
                    """, (user_id,))
                    result = cur.fetchone()
                    cluster_id = result[0] if result else 1
                    cur.close()
                    conn.close()
                    print(f"Found cluster_id from database: {cluster_id}")
                except Exception as e:
                    print(f"Error finding cluster_id: {e}")
                    cluster_id = 1  # Default fallback
            
            print(f"Redirecting to completion: user_id={user_id}, cluster_id={cluster_id}, roleplay_id={roleplay_id}")
            
            return redirect(url_for('roleplay_complete', 
                                  user_id=user_id,
                                  cluster_id=cluster_id,
                                  roleplay_id=roleplay_id))
        else:
            if context["data"]["tip"] is not None:
                tip = context["data"]["tip"]
                # Translate tip if not in English
                if selected_language != 'English':
                    tip = translate_text(tip, selected_language)
                context["tip"] = tip

        # Pass voice configuration to template
        context["input_type"] = session.get('input_type', 'audio')  # Default to audio
        context["available_languages"] = session.get('available_languages', 'English')
        context["voice_enabled"] = context["input_type"] == 'audio'
        context["selected_language"] = selected_language  # Pass to template for display
        context["max_interaction_time"] = session.get('max_interaction_time', 300)
        context["max_total_time"] = session.get('max_total_time', 1800)
        
        print(f"DEBUG AUDIO: input_type={context['input_type']}, voice_enabled={context['voice_enabled']}")

        return render_template("chatbot.html", context = context, form = form)
    else:
        return render_template('404.html', title='Error')

@app.route('/admin/register', methods=['GET', 'POST'])
def admin_register():
    """Admin registration page"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        username = request.form.get('username')
        
        if not email or not password or not username:
            flash('All fields are required')
            return render_template('admin_register.html')
        
        if password != confirm_password:
            flash('Passwords do not match')
            return render_template('admin_register.html')
        
        # Check if user already exists
        existing_user = get_user_by_email(email)
        if existing_user:
            flash('Email already registered')
            return render_template('admin_register.html')
        
        # Create admin user
        result = create_user(email, password, username, is_admin=True)
        
        if result:
            flash('Admin account created successfully! Please login.')
            return redirect(url_for('admin_login'))
        else:
            flash('Error creating admin account. Please try again.')
            return render_template('admin_register.html')
    
    return render_template('admin_register.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login page"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            flash('Email and password are required')
            return render_template('admin_login.html')
        
        # Authenticate user
        user = get_user_id(email, password)
        
        if user and user['is_admin'] == 1:
            # Set session for admin
            session['user_id'] = user['id']
            session['is_admin'] = user['is_admin']
            flash('Welcome Admin!')
            return redirect(url_for('admin'))
        else:
            flash('Invalid admin credentials or insufficient permissions')
            return render_template('admin_login.html')
    
    return render_template('admin_login.html')

@app.route('/admin/user/<int:user_id>/impersonate')
@admin_required
def admin_impersonate_user(user_id):
    """Allow admin to view site as a specific user"""
    # Store admin session info
    admin_id = session.get('user_id')
    session['impersonating_from_admin'] = admin_id
    
    # Set session as this user
    session['user_id'] = user_id
    session.pop('is_admin', None)  # Remove admin flag temporarily
    
    # Redirect to user's dashboard
    user_clusters = get_user_clusters(user_id)
    if user_clusters and len(user_clusters) > 0:
        return redirect(url_for('user_cluster_view', user_id=user_id, cluster_id=user_clusters[0][0]))
    else:
        return redirect(url_for('user_dashboard', user_id=user_id))

@app.route('/admin')
@admin_required
def admin():
    roleplays = get_roleplays()
    if roleplays is None:
        roleplays = []
    return render_template('admin.html', roleplays=roleplays)


@app.route('/adminview', methods=['GET'])
@admin_required
def adminview_new():
    # Show create new roleplay form
    return render_template('adminview.html', roleplay=None, config=None)

@app.route('/adminview/<string:id>', methods=['GET'])
@admin_required
def adminview(id):
    if id is not None:
        # Get basic roleplay data
        roleplay = get_roleplay(id)
        # Get configuration data separately
        config = get_roleplay_config(id)
        return render_template('adminview.html', roleplay=roleplay, config=config)
    return render_template('adminview.html', roleplay=None, config=None)

@app.route("/admin/delete/<int:id>", methods=['GET'])
def delete(id):
    if delete_roleplay(id):
        flash('Roleplay ' + str(id) + ' has been successfully deleted!')
    else:
        flash('Roleplay ' + str(id) + ' could not be deleted!')
    return redirect(url_for('admin'))

@app.route('/adminview', methods=['POST'])
@admin_required
def upload_files():
    import os

    # Ensure upload folders exist
    os.makedirs(app.config['UPLOAD_PATH_ROLEPLAY'], exist_ok=True)
    os.makedirs(app.config['UPLOAD_PATH_IMAGES'], exist_ok=True)
    os.makedirs(app.config['UPLOAD_PATH_COMP'], exist_ok=True)

    files = request.files.to_dict()
    form = request.form.to_dict()

    # Validate required fields
    try:
        # ID is now optional - will be auto-generated if not provided
        id = form.get('id', '').strip()
        if not id:
            id = None  # Will trigger auto-generation
        name = form['name']
        scenario = form['scenario']
        person_name = form['person_name']
    except Exception as e:
        flash("Missing required form fields.")
        return redirect(request.referrer or url_for('adminview'))

    roleplay_file_path = ''
    image_file_path = ''
    scenario_file_path = ''
    logo_path = ''

    # Handle roleplay file upload
    if files.get("roleplay_file"):
        # Use temporary ID for file naming if ID not yet assigned
        file_id = id if id else f"temp_{int(time.time())}"
        roleplay_file = f"{file_id}_{int(time.time())}_{files['roleplay_file'].filename}"
        # Replace forward slashes in ID to prevent subdirectory creation
        roleplay_file = roleplay_file.replace('/', '_').replace('\\', '_')
        roleplay_file_path = os.path.join(app.config['UPLOAD_PATH_ROLEPLAY'], roleplay_file)
        file_ext = os.path.splitext(roleplay_file)[1].lower()
        if file_ext not in [ext.lower() for ext in app.config['UPLOAD_EXTENSIONS_ROLEPLAY']]:
            flash("Invalid roleplay file extension.")
            return redirect(request.referrer or url_for('adminview'))
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(roleplay_file_path), exist_ok=True)
        
        try:
            files['roleplay_file'].save(roleplay_file_path)
        except PermissionError:
            flash(f"⚠️ Cannot save roleplay file - it may be open in another program. Please close the file and try again.")
            return redirect(request.referrer or url_for('adminview'))
        except Exception as e:
            flash(f"Error saving roleplay file: {str(e)}")
            return redirect(request.referrer or url_for('adminview'))

    # Handle image file upload
    if files.get("image_file"):
        # Use temporary ID for file naming if ID not yet assigned
        file_id = id if id else f"temp_{int(time.time())}"
        image_file = f"{file_id}_{int(time.time())}_{files['image_file'].filename}"
        # Replace forward slashes in ID to prevent subdirectory creation
        image_file = image_file.replace('/', '_').replace('\\', '_')
        image_file_path = os.path.join(app.config['UPLOAD_PATH_IMAGES'], image_file)
        file_ext = os.path.splitext(image_file)[1].lower()
        if file_ext not in [ext.lower() for ext in app.config['UPLOAD_EXTENSIONS_IMAGES']]:
            flash("Invalid image file extension.")
            return redirect(request.referrer or url_for('adminview'))
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(image_file_path), exist_ok=True)
        
        try:
            files['image_file'].save(image_file_path)
        except PermissionError:
            flash(f"⚠️ Cannot save image file - it may be open in another program. Please close the file and try again.")
            return redirect(request.referrer or url_for('adminview'))
        except Exception as e:
            flash(f"Error saving image file: {str(e)}")
            return redirect(request.referrer or url_for('adminview'))

    # Handle scenario file upload (optional document for users to download)
    if files.get("scenario_file"):
        file_id = id if id else f"temp_{int(time.time())}"
        scenario_file = f"{file_id}_{int(time.time())}_{files['scenario_file'].filename}"
        scenario_file = scenario_file.replace('/', '_').replace('\\', '_')
        scenario_file_path = os.path.join(app.config['UPLOAD_PATH_IMAGES'], scenario_file)  # Using images folder
        file_ext = os.path.splitext(scenario_file)[1].lower()
        allowed_scenario_exts = ['.pdf', '.doc', '.docx', '.txt', '.xls', '.xlsx']
        if file_ext not in allowed_scenario_exts:
            flash("Invalid scenario file extension. Please use pdf, doc, docx, txt, xls, or xlsx.")
            return redirect(request.referrer or url_for('adminview'))
        
        os.makedirs(os.path.dirname(scenario_file_path), exist_ok=True)
        
        try:
            files['scenario_file'].save(scenario_file_path)
        except PermissionError:
            flash(f"⚠️ Cannot save scenario file - it may be open in another program. Please close the file and try again.")
            return redirect(request.referrer or url_for('adminview'))
        except Exception as e:
            flash(f"Error saving scenario file: {str(e)}")
            return redirect(request.referrer or url_for('adminview'))

    # Handle roleplay logo upload (image for tile display)
    if files.get("roleplay_logo"):
        file_id = id if id else f"temp_{int(time.time())}"
        logo_file = f"{file_id}_{int(time.time())}_logo_{files['roleplay_logo'].filename}"
        logo_file = logo_file.replace('/', '_').replace('\\', '_')
        logo_path = os.path.join(app.config['UPLOAD_PATH_IMAGES'], logo_file)
        file_ext = os.path.splitext(logo_file)[1].lower()
        if file_ext not in [ext.lower() for ext in app.config['UPLOAD_EXTENSIONS_IMAGES']]:
            flash("Invalid logo file extension. Please use an image file.")
            return redirect(request.referrer or url_for('adminview'))
        
        os.makedirs(os.path.dirname(logo_path), exist_ok=True)
        
        try:
            files['roleplay_logo'].save(logo_path)
        except PermissionError:
            flash(f"⚠️ Cannot save logo file - it may be open in another program. Please close the file and try again.")
            return redirect(request.referrer or url_for('adminview'))
        except Exception as e:
            flash(f"Error saving logo file: {str(e)}")
            return redirect(request.referrer or url_for('adminview'))

    # Validate Excel files with enhanced validator that stores data in arrays
    validation_errors = []
    force_upload = request.form.get('force_upload') == 'true'  # Check if admin wants to force upload
    
    if roleplay_file_path and image_file_path:
        try:
            from app.enhanced_excel_validator import validate_excel_files_detailed
            is_valid, detailed_report, validation_data = validate_excel_files_detailed(roleplay_file_path, image_file_path)

            # DEBUG: Print validation results to console
            print(f"\n🔍 VALIDATION DEBUG:")
            print(f"   File paths: {roleplay_file_path}, {image_file_path}")
            print(f"   Is valid: {is_valid}")
            print(f"   Force upload: {force_upload}")
            print(f"   Errors found: {len(validation_data.get('errors', []))}")
            print(f"   Warnings found: {len(validation_data.get('warnings', []))}")
            for error in validation_data.get('errors', []):
                print(f"   ERROR: {error}")
            print(f"🔍 END DEBUG\n")

            if not is_valid and not force_upload:
                # Show validation errors but don't delete files - let admin decide
                validation_has_errors = True
                
                # Check if this is a structural validation failure
                if "STRUCTURAL VALIDATION FAILED:" in detailed_report:
                    # Extract structural errors from detailed_report
                    structural_errors = detailed_report.split("STRUCTURAL VALIDATION FAILED:\n")[1].strip().split('\n')
                    
                    print(f"📢 CRITICAL STRUCTURAL ERRORS: {len(structural_errors)} errors")
                    flash("❌ STRUCTURAL VALIDATION FAILED - Critical structure issues found")
                    flash("Excel file structure does not match required format.")
                    
                    for i, error in enumerate(structural_errors[:10]):  # Show first 10 structural errors
                        if error.strip():
                            error_msg = f"   • {error.strip()}"
                            flash(error_msg)
                            print(f"📢 ERROR {i+1}: {error_msg}")
                    
                    if len(structural_errors) > 10:
                        flash(f"   ... and {len(structural_errors) - 10} more structural issues.")
                    
                    # Delete files for structural errors - these are critical
                    if os.path.exists(roleplay_file_path):
                        os.remove(roleplay_file_path)
                    if os.path.exists(image_file_path):
                        os.remove(image_file_path)
                    
                    return render_template('adminview.html', roleplay=None, config=None)
                
                else:
                    # Content validation errors - allow admin to proceed
                    errors = validation_data.get('errors', [])
                    warnings = validation_data.get('warnings', [])
                    
                    if errors:
                        flash(f"⚠️ Validation found {len(errors)} missing/incorrect data fields:")
                        for error in errors[:10]:
                            flash(f"   • {error}")
                        if len(errors) > 10:
                            flash(f"   ... and {len(errors) - 10} more issues.")
                    
                    if warnings:
                        flash(f"ℹ️ {len(warnings)} warnings (non-critical)")
                    
                    flash("⚠️ You can proceed anyway, but the roleplay may not work correctly.")
                    flash("✓ To proceed with upload despite errors, click 'Save & Force Upload' below.")
                
                # Print full detailed report to console for developer debugging
                print("\n" + "="*80)
                print("FULL EXCEL VALIDATION REPORT:")
                print("="*80)
                print(detailed_report)
                print("="*80 + "\n")
            
            # If validation passed OR admin forced upload, show success message
            if is_valid or force_upload:
                # Show success message with data summary
                roleplay_interactions = len(validation_data.get('roleplay_data', []))
                image_interactions = len(validation_data.get('image_data', []))
                
                if force_upload and not is_valid:
                    flash(f"⚠️ Files uploaded WITH VALIDATION WARNINGS ({len(validation_data.get('errors', []))} issues)")
                    success_msg = f"Proceeding with {roleplay_interactions} roleplay interactions (may have missing data)"
                else:
                    success_msg = f"✅ Excel files validated successfully! Found {roleplay_interactions} roleplay interactions"
                
                if image_interactions > 0:
                    success_msg += f" and {image_interactions} image interactions"
                flash(success_msg)

        except Exception as e:
            # Delete uploaded files if validation fails
            if os.path.exists(roleplay_file_path):
                os.remove(roleplay_file_path)
            if os.path.exists(image_file_path):
                os.remove(image_file_path)
            flash(f"Excel validation error: {str(e)}")
            print(f"Excel validation exception: {str(e)}")
            return redirect(request.referrer or url_for('adminview'))
    elif roleplay_file_path:
        # Validate just the roleplay file with enhanced validator
        try:
            from app.enhanced_excel_validator import validate_excel_files_detailed
            is_valid, detailed_report, validation_data = validate_excel_files_detailed(roleplay_file_path)

            # DEBUG: Print validation results to console
            print(f"\n🔍 ROLEPLAY VALIDATION DEBUG:")
            print(f"   File path: {roleplay_file_path}")
            print(f"   Is valid: {is_valid}")
            print(f"   Errors found: {len(validation_data.get('errors', []))}")
            for error in validation_data.get('errors', []):
                print(f"   ERROR: {error}")
            print(f"🔍 END DEBUG\n")

            if not is_valid:
                if os.path.exists(roleplay_file_path):
                    os.remove(roleplay_file_path)
                
                # Check if this is a structural validation failure
                if "STRUCTURAL VALIDATION FAILED:" in detailed_report:
                    # Extract structural errors from detailed_report
                    structural_errors = detailed_report.split("STRUCTURAL VALIDATION FAILED:\n")[1].strip().split('\n')
                    
                    print(f"📢 FLASHING ROLEPLAY STRUCTURAL ERRORS: {len(structural_errors)} errors")
                    flash("❌ STRUCTURAL VALIDATION FAILED:")
                    flash("Roleplay Excel file structure does not match required format.")
                    
                    for i, error in enumerate(structural_errors[:10]):  # Show first 10 structural errors
                        if error.strip():
                            error_msg = f"   • {error.strip()}"
                            flash(error_msg)
                            print(f"📢 FLASHED ROLEPLAY ERROR {i+1}: {error_msg}")
                    
                    if len(structural_errors) > 10:
                        flash(f"   ... and {len(structural_errors) - 10} more structural issues.")
                    
                    print(f"📢 TOTAL ROLEPLAY FLASH MESSAGES SENT: {len(structural_errors[:10]) + 2}")
                
                else:
                    # Handle content validation errors
                    flash("Roleplay Excel file validation failed with detailed analysis:")
                    
                    errors = validation_data.get('errors', [])
                    if errors:
                        flash(f"❌ Missing Data Found ({len(errors)}) - Must be fixed:")
                        for error in errors[:15]:
                            flash(f"   • {error}")
                        if len(errors) > 15:
                            flash(f"   ... and {len(errors) - 15} more missing data issues.")
                
                # Print full report for debugging
                print("\n" + "="*80)
                print("ROLEPLAY EXCEL VALIDATION REPORT:")
                print("="*80)
                print(detailed_report)
                print("="*80 + "\n")
                
                # Instead of redirect, render template directly to preserve flash messages
                return render_template('adminview.html', roleplay=None, config=None)
            else:
                # Success with data summary - no improvement suggestions
                roleplay_interactions = len(validation_data.get('roleplay_data', []))
                
                flash(f"✅ Roleplay Excel validated successfully! Found {roleplay_interactions} interactions")

        except Exception as e:
            if os.path.exists(roleplay_file_path):
                os.remove(roleplay_file_path)
            flash(f"Roleplay Excel validation error: {str(e)}")
            print(f"Roleplay Excel validation exception: {str(e)}")
            return redirect(request.referrer or url_for('adminview'))    # Handle competency file upload
    if files.get("comp_file"):
        comp_file_path = os.path.join(app.config['UPLOAD_PATH_COMP'], 'Competency descriptions.xlsx')
        file_ext = os.path.splitext(files['comp_file'].filename)[1].lower()
        if file_ext not in [ext.lower() for ext in app.config['UPLOAD_EXTENSIONS_COMP']]:
            flash("Invalid competency file extension.")
            return redirect(request.referrer or url_for('adminview'))
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(comp_file_path), exist_ok=True)
        
        try:
            files['comp_file'].save(comp_file_path)
        except PermissionError:
            flash("⚠️ Cannot save competency file - the file is currently open in another program. Please close 'Competency descriptions.xlsx' and try again.")
            return redirect(request.referrer or url_for('adminview'))
        except Exception as e:
            flash(f"Error saving competency file: {str(e)}")
            return redirect(request.referrer or url_for('adminview'))

    # Handle ideal video upload
    ideal_video_path = ''
    if files.get("ideal_video"):
        # Use temporary ID for file naming if ID not yet assigned
        file_id = id if id else f"temp_{int(time.time())}"
        ideal_video_file = f"{file_id}_{int(time.time())}_{files['ideal_video'].filename}"
        # Replace forward slashes in ID to prevent subdirectory creation
        ideal_video_file = ideal_video_file.replace('/', '_').replace('\\', '_')
        ideal_video_path = os.path.join(app.config['UPLOAD_PATH_IMAGES'], ideal_video_file)  # Using images folder for videos too
        file_ext = os.path.splitext(ideal_video_file)[1].lower()
        if file_ext not in ['.mp4', '.avi', '.mov', '.wmv']:
            flash("Invalid video file extension. Please use mp4, avi, mov, or wmv.")
            return redirect(request.referrer or url_for('adminview'))
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(ideal_video_path), exist_ok=True)
        
        try:
            files['ideal_video'].save(ideal_video_path)
        except PermissionError:
            flash(f"⚠️ Cannot save video file - it may be open in another program. Please close the file and try again.")
            return redirect(request.referrer or url_for('adminview'))
        except Exception as e:
            flash(f"Error saving video file: {str(e)}")
            return redirect(request.referrer or url_for('adminview'))

    # Save to database
    new_id = create_or_update(id, name, person_name, scenario, roleplay_file_path, image_file_path, scenario_file_path, logo_path)
    if new_id is None:
        # Debug info for why DB insert/update failed
        print("create_or_update returned None for inputs:")
        try:
            print({
                'id': id,
                'name': name,
                'person_name': person_name,
                'scenario_len': len(scenario) if scenario is not None else 0,
                'roleplay_file_path': roleplay_file_path,
                'roleplay_file_exists': os.path.exists(roleplay_file_path) if roleplay_file_path else False,
                'image_file_path': image_file_path,
                'image_file_exists': os.path.exists(image_file_path) if image_file_path else False
            })
        except Exception as e:
            print("Error while printing debug info:", e)
        flash("Roleplay could not be added. See server logs for details.")
        return redirect(request.referrer or url_for('adminview'))
    
    # Handle roleplay configuration
    try:
        # Build selected languages JSON
        selected_languages = []
        available_languages = ['English', 'Hindi', 'Tamil', 'Telugu', 'Kannada', 'Malayalam', 'Bengali', 'Marathi']
        for lang in available_languages:
            if form.get(f'lang_{lang.lower()}'):
                selected_languages.append(lang)
        
        config_data = {
            'input_type': form.get('input_type', 'text'),
            'audio_rerecord_attempts': int(form.get('audio_rerecord_attempts', 3)),
            'available_languages': str(selected_languages).replace("'", '"'),  # Convert to JSON string
            'max_interaction_time': int(form.get('max_interaction_time', 300)),
            'max_total_time': int(form.get('max_total_time', 1800)),
            'repeat_attempts_allowed': int(form.get('repeat_attempts_allowed', 1)),
            'score_type': form.get('score_type', 'last'),
            'show_ideal_video': form.get('show_ideal_video') == 'on',
            'ideal_video_path': ideal_video_path,
            'voice_assessment_enabled': form.get('voice_assessment_enabled') == 'on',
            'difficulty_level': form.get('difficulty_level', 'easy')
        }
        
        create_or_update_roleplay_config(new_id, config_data)
        
    except Exception as e:
        print(f"Error saving roleplay config: {str(e)}")
        flash("Roleplay saved but configuration failed to save")
    
    flash(f'Roleplay has been successfully added!')
    return redirect(url_for('admin'))
    files = {}
    if request.files:
        files = request.files.to_dict()
    form = request.form.to_dict()
    id = int(form['id'])
    name = form['name']
    scenario = form['scenario']
    person_name = form['person_name']


    roleplay_file_path = ''
    image_file_path = ''

    if files.get("roleplay_file"):
        roleplay_file = str(id) + "_" + str(int(time.time())) + "_" + str(files['roleplay_file'].filename)
        # Replace forward slashes in ID to prevent subdirectory creation
        roleplay_file = roleplay_file.replace('/', '_').replace('\\', '_')
        roleplay_file_path = os.path.join(app.config['UPLOAD_PATH_ROLEPLAY'], roleplay_file)
        file_ext = os.path.splitext(roleplay_file)[1]
        if file_ext not in app.config['UPLOAD_EXTENSIONS_ROLEPLAY']:
            abort(400)
        # Ensure the directory exists
        os.makedirs(os.path.dirname(roleplay_file_path), exist_ok=True)
        files['roleplay_file'].save(roleplay_file_path)
    if files.get("image_file"):
        image_file = str(id) + "_" + str(int(time.time())) + "_" + str(files['image_file'].filename)
        # Replace forward slashes in ID to prevent subdirectory creation
        image_file = image_file.replace('/', '_').replace('\\', '_')
        image_file_path = os.path.join(app.config['UPLOAD_PATH_IMAGES'], image_file)
        file_ext = os.path.splitext(image_file)[1]
        if file_ext not in app.config['UPLOAD_EXTENSIONS_IMAGES']:
            abort(400)
        # Ensure the directory exists
        os.makedirs(os.path.dirname(image_file_path), exist_ok=True)
        files['image_file'].save(image_file_path)
    if files.get("comp_file"):
        comp_file_path = os.path.join(app.config['UPLOAD_PATH_COMP'], 'Competency descriptions.xlsx')
        file_ext = os.path.splitext(files['comp_file'].filename)[1]
        if file_ext not in app.config['UPLOAD_EXTENSIONS_COMP']:
            abort(400)
        # Ensure the directory exists
        os.makedirs(os.path.dirname(comp_file_path), exist_ok=True)
        files['comp_file'].save(comp_file_path)
    id = create_or_update(id, name, person_name, scenario, roleplay_file_path, image_file_path, '', '')
    if id is None:
        print("create_or_update returned None for inputs (fallback branch):")
        try:
            print({
                'id': id,
                'name': name,
                'person_name': person_name,
                'scenario_len': len(scenario) if scenario is not None else 0,
                'roleplay_file_path': roleplay_file_path,
                'roleplay_file_exists': os.path.exists(roleplay_file_path) if roleplay_file_path else False,
                'image_file_path': image_file_path,
                'image_file_exists': os.path.exists(image_file_path) if image_file_path else False
            })
        except Exception as e:
            print("Error while printing debug info:", e)
        flash("Roleplay could not be added. See server logs for details.")
        return redirect(request.referrer)
    flash('Roleplay ' + str(id) + ' has been successfully added!')
    return redirect(url_for('admin'))

@app.route("/thinking")
def thinking():
    """Show thinking/loading page while AI processes response"""
    if 'roleplay_id' not in session or 'interaction_number' not in session:
        return redirect(url_for('index'))
    # The `thinking.html` template was removed. Redirect back to the chatbot
    # which will show the current state; client-side scripts should handle
    # any loading indicators. This preserves existing links to /thinking.
    return redirect(url_for('chatbot', roleplay_id=session.get('roleplay_id'), interaction_num=session.get('interaction_number', 1)))

@app.route("/process_response")
def process_response():
    """Show thinking page first, then process the user response"""
    if 'user_input' not in session:
        return redirect(url_for('index'))
    # Previously this returned the removed thinking template and relied on
    # client-side JS to call /get_ai_response. Instead, run the same
    # processing synchronously here and redirect to the updated chatbot
    # page so the user sees the next interaction immediately.
    success, redirect_url, message = _process_ai_and_update_session()
    if not success:
        # Keep user on chatbot and show flash message
        flash(message)
        return redirect(url_for('chatbot', roleplay_id=session.get('roleplay_id'), interaction_num=session.get('interaction_number', 1)))
    return redirect(redirect_url)

@app.route("/get_ai_response")
def get_ai_response():
    """Process the AI response and return JSON"""
    if 'user_input' not in session:
        return redirect(url_for('index'))
    # Reuse the same processing logic but return JSON for client-side callers
    success, redirect_url, message = _process_ai_and_update_session()
    if not success:
        return jsonify({"success": False, "message": message})
    return jsonify({"success": True, "redirect_url": redirect_url})


def _process_ai_and_update_session():
    """Internal helper: run AI processing and update session state.

    Returns: (success: bool, redirect_url_or_none: str or None, message: str or None)
    """
    try:
        reader_obj = reader.excel.ExcelReader(session["exr_param0"], competency_descriptions, session["exr_param2"])
        interactor_obj = interface.interact.LLMInteractor(openai.api_key, reader_obj.get_system_prompt(), session['roleplay_id'])
        ai_obj = interface.openai.Conversation(reader_obj, interactor_obj)

        resp = ai_obj.chat(session['user_input'], session["interaction_number"])
        if resp == False:
            return False, None, "Invalid Input!! Improve your response!"
        # Save the response data
        chathistory_id = create_chat_entry(session['user_input'], resp["comp"])
        scoremaster_id = create_score_master(chathistory_id, resp["score"])

        name_change_dict = {
            "Sentiment": "Sentiment/Keyword Match Score",
            "Instruction Following": "Aligned to best practice score"
        }
        session["last_round_result"] = {}
        for competency in resp["score_breakdown"]:
            score_name = competency
            if competency in name_change_dict:
                score_name = name_change_dict[competency]
            session["last_round_result"][score_name] = resp["score_breakdown"][competency]
            create_score_breakdown(scoremaster_id, score_name, resp["score_breakdown"][competency])

        session["score"] = resp["score"]
        session["comp_dialogue"] = resp["comp"]
        session["image_interaction_number"] = session["interaction_number"]
        session["interaction_number"] = resp["interaction_number"]

        # Clean up
        session.pop('user_input', None)

        redirect_url = url_for('chatbot', roleplay_id=session['roleplay_id'], interaction_num=session['interaction_number'])
        return True, redirect_url, None

    except Exception as e:
        print(e)
        return False, None, "Sorry something went wrong!"

# Cluster Management Routes

@app.route('/admin/clusters')
@admin_required
def admin_clusters():
    """Display all clusters"""
    clusters = get_clusters()
    if clusters is None:
        clusters = []
    return render_template('admin_clusters.html', clusters=clusters)

@app.route('/admin/clusters/new', methods=['GET'])
@admin_required
def admin_cluster_new():
    """Show form to create new cluster"""
    roleplays = get_roleplays()
    if roleplays is None:
        roleplays = []
    
    users = get_all_users()
    if users is None:
        users = []
    
    return render_template('admin_cluster_form.html', cluster=None, roleplays=roleplays, users=users)

@app.route('/admin/clusters/<int:cluster_id>/edit', methods=['GET'])
@admin_required
def admin_cluster_edit(cluster_id):
    """Show form to edit cluster"""
    cluster = get_cluster(cluster_id)
    if not cluster:
        flash('Cluster not found')
        return redirect(url_for('admin_clusters'))
    
    roleplays = get_roleplays()
    cluster_roleplays = get_cluster_roleplays(cluster_id)
    
    users = get_all_users()
    if users is None:
        users = []
    
    cluster_users = get_cluster_users(cluster_id)
    if cluster_users is None:
        cluster_users = []
    
    return render_template('admin_cluster_form.html', 
                         cluster=cluster, 
                         roleplays=roleplays, 
                         cluster_roleplays=cluster_roleplays,
                         users=users,
                         cluster_users=cluster_users)

@app.route('/admin/clusters', methods=['POST'])
@admin_required
def admin_cluster_create():
    """Create or update cluster"""
    try:
        form_data = request.form.to_dict()
        cluster_id = form_data.get('cluster_id')
        
        if cluster_id:  # Edit existing cluster
            cluster_id = int(cluster_id)
            
            # Update cluster name and type
            update_cluster(
                id=cluster_id,
                name=form_data['name'],
                cluster_type=form_data.get('type', 'assessment')
            )
            
            # Update roleplay assignments
            # First, remove all existing roleplays
            existing_roleplays = get_cluster_roleplays(cluster_id)
            if existing_roleplays:
                for roleplay in existing_roleplays:
                    remove_roleplay_from_cluster(cluster_id, roleplay[0])
            
            # Add selected roleplays
            selected_roleplays = request.form.getlist('selected_roleplays')
            print(f"DEBUG: Adding {len(selected_roleplays)} roleplays to cluster {cluster_id}")
            for idx, roleplay_id in enumerate(selected_roleplays):
                print(f"DEBUG: Adding roleplay {roleplay_id} at position {idx + 1}")
                result = add_roleplay_to_cluster(cluster_id, roleplay_id, idx + 1)
                print(f"DEBUG: Result of adding roleplay {roleplay_id}: {result}")
            
            # Update user assignments
            # First, remove all existing users
            existing_users = get_cluster_users(cluster_id)
            if existing_users:
                for user in existing_users:
                    remove_cluster_from_user(user[0], cluster_id)
            
            # Add selected users
            selected_users = request.form.getlist('selected_users')
            print(f"DEBUG: Assigning cluster {cluster_id} to {len(selected_users)} users: {selected_users}")
            for user_id in selected_users:
                print(f"DEBUG: Assigning cluster {cluster_id} to user {user_id}")
                result = assign_cluster_to_user(int(user_id), cluster_id)
                print(f"DEBUG: Result of assigning cluster to user {user_id}: {result}")
            
            flash('Cluster updated successfully!')
            
        else:  # Create new cluster
            new_cluster_id = create_cluster(
                name=form_data['name'],
                cluster_id=None,  # Auto-generate cluster ID
                cluster_type=form_data['type']
            )
            
            if new_cluster_id:
                # Add selected roleplays to cluster
                selected_roleplays = request.form.getlist('selected_roleplays')
                print(f"DEBUG: Adding {len(selected_roleplays)} roleplays to new cluster {new_cluster_id}")
                for idx, roleplay_id in enumerate(selected_roleplays):
                    print(f"DEBUG: Adding roleplay {roleplay_id} at position {idx + 1}")
                    result = add_roleplay_to_cluster(new_cluster_id, roleplay_id, idx + 1)
                    print(f"DEBUG: Result of adding roleplay {roleplay_id}: {result}")
                
                # Add selected users to cluster
                selected_users = request.form.getlist('selected_users')
                print(f"DEBUG: Assigning new cluster {new_cluster_id} to {len(selected_users)} users: {selected_users}")
                for user_id in selected_users:
                    print(f"DEBUG: Assigning cluster {new_cluster_id} to user {user_id}")
                    result = assign_cluster_to_user(int(user_id), new_cluster_id)
                    print(f"DEBUG: Result of assigning cluster to user {user_id}: {result}")
                
                flash('Cluster created successfully!')
            else:
                flash('Failed to create cluster')
        
        return redirect(url_for('admin_clusters'))
        
    except Exception as e:
        print(f"Error creating cluster: {str(e)}")
        flash('Error creating cluster')
        return redirect(url_for('admin_clusters'))

@app.route('/admin/clusters/<int:cluster_id>/delete', methods=['GET'])
@admin_required
def admin_cluster_delete(cluster_id):
    """Delete cluster"""
    if delete_cluster(cluster_id):
        flash('Cluster deleted successfully!')
    else:
        flash('Failed to delete cluster')
    return redirect(url_for('admin_clusters'))

# User Management Routes

@app.route('/admin/users')
@admin_required
def admin_users():
    """Display all users"""
    users = get_all_users()
    if users is None:
        users = []
    return render_template('admin_users.html', users=users)

@app.route('/admin/users/<int:user_id>')
@admin_required
def admin_user_detail(user_id):
    """View and manage user's cluster assignments"""
    user = get_user(user_id)
    if not user:
        flash('User not found')
        return redirect(url_for('admin_users'))
    
    # Get all clusters
    all_clusters = get_clusters()
    if all_clusters is None:
        all_clusters = []
    
    # Get user's assigned clusters
    user_clusters = get_user_clusters(user_id)
    if user_clusters is None:
        user_clusters = []
    
    # Create a set of assigned cluster IDs for easy lookup
    assigned_cluster_ids = {cluster[0] for cluster in user_clusters}
    
    return render_template('admin_user_detail.html', 
                         user=user, 
                         all_clusters=all_clusters,
                         user_clusters=user_clusters,
                         assigned_cluster_ids=assigned_cluster_ids)

@app.route('/admin/users/<int:user_id>/assign-cluster', methods=['POST'])
@admin_required
def admin_assign_cluster(user_id):
    """Assign a cluster to a user"""
    try:
        cluster_id = request.form.get('cluster_id')
        if not cluster_id:
            flash('Please select a cluster')
            return redirect(url_for('admin_user_detail', user_id=user_id))
        
        if assign_cluster_to_user(user_id, cluster_id):
            flash('Cluster assigned successfully!')
        else:
            flash('Failed to assign cluster')
    except Exception as e:
        print(f"Error assigning cluster: {str(e)}")
        flash('Error assigning cluster')
    
    return redirect(url_for('admin_user_detail', user_id=user_id))

@app.route('/admin/users/<int:user_id>/remove-cluster/<int:cluster_id>', methods=['GET'])
@admin_required
def admin_remove_cluster(user_id, cluster_id):
    """Remove a cluster from a user"""
    if remove_cluster_from_user(user_id, cluster_id):
        flash('Cluster removed successfully!')
    else:
        flash('Failed to remove cluster')
    return redirect(url_for('admin_user_detail', user_id=user_id))

@app.route('/user/<int:user_id>')
def user_dashboard(user_id):
    """Display all clusters assigned to a user"""
    try:
        user = get_user(user_id)
        if not user:
            flash('User not found')
            return redirect(url_for('index'))
        
        print(f"DEBUG: Loading dashboard for user {user_id}")
        user_clusters = get_user_clusters(user_id)
        print(f"DEBUG: Found {len(user_clusters) if user_clusters else 0} clusters for user {user_id}")
        
        if not user_clusters:
            return render_template('user_dashboard.html', user=user, clusters=[])
        
        # Enrich clusters with roleplay information
        clusters_with_roleplays = []
        for cluster in user_clusters:
            print(f"DEBUG: Processing cluster {cluster[0]} - {cluster[1]}")
            cluster_roleplays = get_cluster_roleplays(cluster[0])
            cluster_dict = {
                'id': cluster[0],
                'name': cluster[1],
                'cluster_id': cluster[2],
                'type': cluster[3],
                'created_at': cluster[4],
                'roleplays': cluster_roleplays
            }
            print(f"DEBUG: Cluster {cluster[0]} has {len(cluster_roleplays)} roleplays")
            clusters_with_roleplays.append(cluster_dict)
        
        return render_template('user_dashboard.html', user=user, clusters=clusters_with_roleplays)
    except Exception as e:
        print(f"Error loading user dashboard: {str(e)}")
        import traceback
        traceback.print_exc()
        return render_template('500.html'), 500

@app.route('/user/<int:user_id>/cluster/<int:cluster_id>')
def user_cluster_view(user_id, cluster_id):
    """Display roleplays in a cluster for a user"""
    try:
        # Get user info
        user = get_user(user_id)
        if not user:
            flash('User not found')
            return redirect(url_for('index'))
        
        # Store user email in session for navbar display
        session['user_email'] = user[1]  # user[1] is the email
        
        # Check if user has access to this cluster
        user_clusters = get_user_clusters(user_id)
        cluster_ids = [c[0] for c in user_clusters] if user_clusters else []
        
        if cluster_id not in cluster_ids:
            flash('You do not have access to this cluster')
            return redirect(url_for('user_dashboard', user_id=user_id))
        
        cluster = get_cluster(cluster_id)
        if not cluster:
            flash('Cluster not found')
            return redirect(url_for('user_dashboard', user_id=user_id))
        
        # Get roleplays in this cluster with their configs
        cluster_roleplays = get_cluster_roleplays(cluster_id)
        
        roleplay_data = []
        for rp in cluster_roleplays:
            config = get_roleplay_config(rp[0])
            
            # Check user's attempts for this roleplay
            conn = mysql.connector.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                user=os.getenv('DB_USER', 'root'),
                password=os.getenv('DB_PASSWORD'),
                database=os.getenv('DB_NAME', 'roleplay')
            )
            cur = conn.cursor()
            
            # Get user's play history for this roleplay in THIS cluster
            cur.execute("""
                SELECT COUNT(*) FROM play 
                WHERE user_id = %s AND roleplay_id = %s AND cluster_id = %s AND status = 'completed'
            """, (user_id, rp[0], cluster_id))
            completed_attempts = cur.fetchone()[0]
            
            # Check if user viewed optimal video in THIS cluster
            cur.execute("""
                SELECT COUNT(*) FROM play 
                WHERE user_id = %s AND roleplay_id = %s AND cluster_id = %s AND status = 'optimal_viewed'
            """, (user_id, rp[0], cluster_id))
            viewed_optimal = cur.fetchone()[0] > 0
            
            # Check if there's an in-progress attempt in THIS cluster
            cur.execute("""
                SELECT COUNT(*) FROM play 
                WHERE user_id = %s AND roleplay_id = %s AND cluster_id = %s AND status = 'in_progress'
            """, (user_id, rp[0], cluster_id))
            has_in_progress = cur.fetchone()[0] > 0
            
            cur.close()
            conn.close()
            
            max_attempts = config[7] if config else 1  # repeat_attempts_allowed
            
            # If viewed optimal, no attempts remaining
            if viewed_optimal:
                attempts_remaining = 0
                can_reattempt = False
            else:
                attempts_remaining = max(0, max_attempts - completed_attempts)
                can_reattempt = attempts_remaining > 0 and completed_attempts > 0
            
            # Determine status
            if viewed_optimal:
                status = 'completed'
            elif completed_attempts > 0:
                status = 'attempted'
            elif has_in_progress:
                status = 'in_progress'
            else:
                status = 'not_started'
            
            roleplay_data.append({
                'id': rp[0],
                'name': rp[1],  # roleplay name
                'person_name': rp[5],  # character name
                'title': rp[5],  # Use person_name as title
                'scenario': rp[4],
                'scenario_file_path': rp[8] if len(rp) > 8 else None,  # scenario file for download
                'logo_path': rp[9] if len(rp) > 9 else None,  # roleplay logo for tile display
                'image_path': rp[3],
                'difficulty': config[12].capitalize() if config and len(config) > 12 and config[12] else 'Easy',  # Get from config
                'order': rp[-1],  # order_sequence from cluster_roleplay
                'status': status,
                'attempts_remaining': attempts_remaining,
                'max_attempts': max_attempts,
                'completed_attempts': completed_attempts,
                'can_reattempt': can_reattempt,
                'has_in_progress': has_in_progress,
                'input_type': config[2] if config else 'text',  # 'audio' or 'text'
                'voice_enabled': config[2] == 'audio' if config else False,
                'show_ideal_video': config[9] if config else False,
                'ideal_video_path': config[10] if config else None,
                'max_interaction_time': config[5] if config else 300,
                'max_total_time': config[6] if config else 1800,
                'available_languages': config[4] if config else '["English"]',
                'config': config
            })
        
        # Sort by order_sequence
        roleplay_data.sort(key=lambda x: x['order'])
        
        return render_template('user_cluster_dashboard.html',
                             user_id=user_id,
                             cluster=cluster,
                             roleplays=roleplay_data)
                             
    except Exception as e:
        print(f"Error loading cluster: {str(e)}")
        import traceback
        traceback.print_exc()
        return render_template('500.html'), 500


@app.route('/user/<int:user_id>/cluster/<int:cluster_id>/roleplay/<path:roleplay_id>/complete')
def roleplay_complete(user_id, cluster_id, roleplay_id):
    """Handle roleplay completion - redirect to new completion page"""
    return redirect(url_for('roleplay_completion', user_id=user_id, cluster_id=cluster_id, roleplay_id=roleplay_id))


@app.route('/user/<int:user_id>/cluster/<int:cluster_id>/roleplay/<path:roleplay_id>/submit')
def submit_and_next(user_id, cluster_id, roleplay_id):
    """Submit current roleplay scores and redirect to completion page"""
    try:
        # Post scores to Sgate
        if 'play_id' in session:
            post_attempt_data(session['play_id'])
        
        # Get roleplay configuration to check attempts
        from app.queries import get_roleplay_with_config
        roleplay = get_roleplay_with_config(roleplay_id)
        
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME', 'roleplay')
        )
        cur = conn.cursor()
        
        # Update play status
        if 'play_id' in session:
            cur.execute("""
                UPDATE play SET status = 'completed', end_time = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (session['play_id'],))
        
        conn.commit()
        cur.close()
        conn.close()
        
        flash('Scores submitted successfully!')
        return redirect(url_for('roleplay_completion', user_id=user_id, cluster_id=cluster_id, roleplay_id=roleplay_id))
        
    except Exception as e:
        print(f"Error submitting scores: {str(e)}")
        flash('Error submitting scores')
        return redirect(url_for('user_cluster_view', user_id=user_id, cluster_id=cluster_id))


@app.route('/user/<int:user_id>/cluster/<int:cluster_id>/roleplay/<path:roleplay_id>/submit_scores', methods=['POST'])
def submit_scores_ajax(user_id, cluster_id, roleplay_id):
    """AJAX endpoint to submit scores when moving to next roleplay"""
    try:
        # Get the most recent in-progress attempt for this roleplay
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME', 'roleplay')
        )
        cur = conn.cursor(dictionary=True)
        
        # Find the in-progress play record
        cur.execute("""
            SELECT id FROM play
            WHERE user_id = %s AND roleplay_id = %s AND status = 'in_progress'
            ORDER BY start_time DESC
            LIMIT 1
        """, (user_id, roleplay_id))
        
        play_record = cur.fetchone()
        
        if play_record:
            play_id = play_record['id']
            
            # TODO: Post scores to Sgate when integration is ready
            # For now, just mark as completed with a placeholder
            # post_attempt_data(play_id)
            
            # Update play status to completed
            cur.execute("""
                UPDATE play SET status = 'completed', end_time = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (play_id,))
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'message': 'Scores submitted successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'No in-progress attempt found'
            })
        
    except Exception as e:
        print(f"Error submitting scores: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        })
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()


@app.route('/user/<int:user_id>/cluster/<int:cluster_id>/roleplay/<path:roleplay_id>/completion')
def roleplay_completion(user_id, cluster_id, roleplay_id):
    """Show roleplay completion page with options"""
    try:
        from app.queries import get_roleplay_with_config
        
        # Get roleplay configuration
        roleplay = get_roleplay_with_config(roleplay_id)
        if not roleplay:
            flash('Roleplay not found')
            return redirect(url_for('user_cluster_view', user_id=user_id, cluster_id=cluster_id))
        
        # Extract configuration values
        max_attempts = roleplay[11] if roleplay[11] is not None else 1  # repeat_attempts_allowed
        show_ideal_video = roleplay[13] if roleplay[13] is not None else False  # show_ideal_video
        ideal_video_path = roleplay[14] if roleplay[14] is not None else None  # ideal_video_path
        
        # Count completed attempts for this user and roleplay
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME', 'roleplay')
        )
        cur = conn.cursor()
        
        # Check if user has viewed optimal video in THIS cluster
        cur.execute("""
            SELECT COUNT(*) FROM play 
            WHERE user_id = %s AND roleplay_id = %s AND cluster_id = %s AND status = 'optimal_viewed'
        """, (user_id, roleplay_id, cluster_id))
        
        has_viewed_optimal = cur.fetchone()[0] > 0
        
        # Count completed attempts for this roleplay in THIS cluster
        cur.execute("""
            SELECT COUNT(*) FROM play 
            WHERE user_id = %s AND roleplay_id = %s AND cluster_id = %s AND status = 'completed'
        """, (user_id, roleplay_id, cluster_id))
        
        completed_attempts = cur.fetchone()[0]
        
        print(f"DEBUG ATTEMPTS: user_id={user_id}, roleplay_id={roleplay_id}, cluster_id={cluster_id}")
        print(f"DEBUG ATTEMPTS: max_attempts={max_attempts}, completed_attempts={completed_attempts}, has_viewed_optimal={has_viewed_optimal}")
        
        # If user has viewed optimal video, they cannot retry
        if has_viewed_optimal:
            attempts_remaining = 0
        else:
            attempts_remaining = max(0, max_attempts - completed_attempts)
        
        print(f"DEBUG ATTEMPTS: attempts_remaining={attempts_remaining}")
        
        cur.close()
        conn.close()
        
        return render_template('roleplay_completion.html',
                             user_id=user_id,
                             cluster_id=cluster_id,
                             roleplay_id=roleplay_id,
                             max_attempts=max_attempts,
                             attempts_remaining=attempts_remaining,
                             show_ideal_video=show_ideal_video,
                             ideal_video_path=ideal_video_path)
    
    except Exception as e:
        print(f"Error in roleplay_completion: {str(e)}")
        flash('Error loading completion page')
        return redirect(url_for('user_cluster_view', user_id=user_id, cluster_id=cluster_id))

@app.route('/user/<int:user_id>/cluster/<int:cluster_id>/roleplay/<path:roleplay_id>/optimal')
def view_optimal_roleplay(user_id, cluster_id, roleplay_id):
    """View optimal roleplay video and mark attempts as exhausted"""
    try:
        from app.queries import get_roleplay_with_config
        
        # Get roleplay configuration
        roleplay = get_roleplay_with_config(roleplay_id)
        if not roleplay:
            flash('Roleplay not found')
            return redirect(url_for('user_cluster_view', user_id=user_id, cluster_id=cluster_id))
        
        ideal_video_path = roleplay[14] if roleplay[14] is not None else None  # ideal_video_path
        
        if not ideal_video_path:
            flash('No optimal roleplay video available')
            return redirect(url_for('roleplay_completion', user_id=user_id, cluster_id=cluster_id, roleplay_id=roleplay_id))
        
        # Mark all remaining attempts as exhausted (user viewed optimal video)
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME', 'roleplay')
        )
        cur = conn.cursor()
        
        # Insert a record to indicate optimal video was viewed
        cur.execute("""
            INSERT INTO play (user_id, roleplay_id, status, start_time, end_time, notes)
            VALUES (%s, %s, 'optimal_viewed', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 'User viewed optimal roleplay video')
        """, (user_id, roleplay_id))
        
        conn.commit()
        cur.close()
        conn.close()
        
        # Render video player page
        return render_template('optimal_roleplay.html',
                             user_id=user_id,
                             cluster_id=cluster_id,
                             roleplay_id=roleplay_id,
                             video_path=ideal_video_path)
    
    except Exception as e:
        print(f"Error in view_optimal_roleplay: {str(e)}")
        flash('Error loading optimal roleplay')
        return redirect(url_for('roleplay_completion', user_id=user_id, cluster_id=cluster_id, roleplay_id=roleplay_id))

@app.route('/test-validation-modal')
def test_validation_modal():
    """Test route to demonstrate the validation modal functionality"""
    
    # Simulate only missing data errors - no improvement suggestions
    flash("❌ Missing Data Found (3) - Must be fixed:")
    flash("   • [Flow:C5] Missing player response 1 for interaction 2")
    flash("   • [Flow:D7] Missing competency mapping 2 for interaction 3")
    flash("   • [Tags:B6] Missing value for 'Meta competencies'")
    
    flash("✅ SUCCESS: Found 5 roleplay interactions and 3 image interactions parsed successfully")
    
    # Render the adminview template to show the modal
    return render_template('adminview.html', roleplay=None, config=None)


@app.route('/admin/send_report/<int:play_id>', methods=['POST'])
@admin_required
def admin_send_report(play_id):
    """Admin route to generate and send performance report"""
    try:
        # Get play information
        play_info = get_play_info(play_id)
        if not play_info:
            flash('Play session not found')
            return redirect(url_for('admin_dashboard'))
        
        user_id = play_info[2]
        roleplay_id = play_info[3]
        
        # Get user information
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME', 'roleplay')
        )
        cur = conn.cursor()
        
        # Get user email
        cur.execute("SELECT id, email FROM user WHERE id = %s", (user_id,))
        user_data = cur.fetchone()
        if not user_data:
            flash('User not found')
            return redirect(url_for('admin_dashboard'))
        
        user_email = user_data[1]
        user_name = user_email.split('@')[0]  # Use email prefix as name if no name field
        
        # Get roleplay details
        roleplay = get_roleplay(roleplay_id)
        if not roleplay:
            flash('Roleplay not found')
            return redirect(url_for('admin_dashboard'))
        
        roleplay_name = roleplay[1]  # name field
        scenario = roleplay[4]  # scenario field
        
        # Get report data (scores and interactions)
        report = query_showreport(play_id)
        interactions = report[0]  # conversation data
        score_breakdown = report[1]  # competencies scores
        overall_score = report[2].get('overall_score', 0)
        
        # Generate PDF report
        report_path = generate_roleplay_report(
            user_name=user_name,
            user_email=user_email,
            roleplay_name=roleplay_name,
            scenario=scenario,
            overall_score=overall_score,
            score_breakdown=score_breakdown,
            interactions=interactions
        )
        
        # Send email with report
        admin_email = session.get('email', os.getenv('SMTP_USERNAME'))
        success = send_report_email(
            to_email=user_email,
            user_name=user_name,
            roleplay_name=roleplay_name,
            overall_score=overall_score,
            report_pdf_path=report_path,
            admin_email=admin_email
        )
        
        cur.close()
        conn.close()
        
        if success:
            flash(f'Report successfully sent to {user_email}')
        else:
            flash('Report generated but email sending failed. Check SMTP settings.')
        
        return redirect(request.referrer or url_for('admin_dashboard'))
        
    except Exception as e:
        print(f"Error sending report: {str(e)}")
        import traceback
        traceback.print_exc()
        flash(f'Error generating/sending report: {str(e)}')
        return redirect(url_for('admin_dashboard'))


def generate_and_send_report_async(play_id, user_id_override=None):
    """
    Generate and send report automatically after roleplay completion
    This can be called asynchronously in the background
    
    Args:
        play_id: The play session ID
        user_id_override: Optional user_id to use if play record has NULL user_id
    """
    # Run in app context to access current_app
    with app.app_context():
        try:
            print(f"DEBUG: Starting report generation for play_id={play_id}, user_id_override={user_id_override}")
            
            # Get play information
            play_info = get_play_info(play_id)
            if not play_info:
                print(f"ERROR: Play session {play_id} not found")
                return False
            
            print(f"DEBUG: Play info retrieved: {play_info}")
            
            # Play table structure: (id, start_time, user_id, ???, roleplay_id, cluster_id, ...)
            # Adjust indices based on actual structure
            user_id = play_info[2]
            
            # roleplay_id appears to be at index 4 based on debug output
            roleplay_id = play_info[4] if len(play_info) > 4 else play_info[3]
            
            print(f"DEBUG: user_id from play={user_id}, roleplay_id={roleplay_id}")
            
            # Check if user_id is None and use override
            if user_id is None:
                if user_id_override:
                    user_id = user_id_override
                    print(f"DEBUG: Using user_id_override={user_id}")
                else:
                    print(f"ERROR: user_id is None for play_id={play_id} and no override provided")
                    # Try to get from session as last resort
                    from flask import session
                    user_id = session.get('user_id')
                    if user_id:
                        print(f"DEBUG: Retrieved user_id={user_id} from session")
                    else:
                        print(f"ERROR: Cannot determine user_id for play_id={play_id}")
                        return False
            
            # Get user information
            conn = mysql.connector.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                user=os.getenv('DB_USER', 'root'),
                password=os.getenv('DB_PASSWORD'),
                database=os.getenv('DB_NAME', 'roleplay')
            )
            cur = conn.cursor()
            
            # Get user email
            cur.execute("SELECT id, email FROM user WHERE id = %s", (user_id,))
            user_data = cur.fetchone()
            if not user_data:
                print(f"ERROR: User {user_id} not found in database")
                cur.close()
                conn.close()
                return False
            
            user_email = user_data[1]
            user_name = user_email.split('@')[0]
            
            print(f"DEBUG: User found - email={user_email}, name={user_name}")
            
            # Get roleplay details
            roleplay = get_roleplay(roleplay_id)
            if not roleplay:
                print(f"ERROR: Roleplay {roleplay_id} not found")
                print(f"DEBUG: Attempting to query roleplay table directly...")
                
                # Try direct query to debug
                try:
                    cur.execute("SELECT * FROM roleplay WHERE id = %s", (roleplay_id,))
                    roleplay = cur.fetchone()
                    if not roleplay:
                        # Try to get any roleplay as fallback for testing
                        cur.execute("SELECT * FROM roleplay LIMIT 1")
                        roleplay = cur.fetchone()
                        if roleplay:
                            print(f"WARNING: Using fallback roleplay: {roleplay[0]}")
                        else:
                            print(f"ERROR: No roleplays found in database")
                            cur.close()
                            conn.close()
                            return False
                except Exception as e:
                    print(f"ERROR: Database query failed: {str(e)}")
                    cur.close()
                    conn.close()
                    return False
            
            roleplay_name = roleplay[1]
            scenario = roleplay[4]
            
            print(f"DEBUG: Roleplay found - name={roleplay_name}")
            
            # Get report data
            report = query_showreport(play_id)
            interactions = report[0]
            score_breakdown_list = report[1]  # List of {"name": X, "score": Y, "total_possible": Z}
            # report[2] is final_score dict with structure: {"overall_score": {"score": X, "total": Y}}
            overall_score_dict = report[2].get('overall_score', {"score": 0, "total": 0})
            overall_score = overall_score_dict.get('score', 0)
            
            # Convert score_breakdown from list to dict format expected by report generator
            # Convert scores to percentage (out of 100)
            score_breakdown = {}
            for item in score_breakdown_list:
                category_name = item['name']
                score = item['score']
                total_possible = item['total_possible']
                # Convert to percentage
                percentage = (score / total_possible * 100) if total_possible > 0 else 0
                score_breakdown[category_name] = round(percentage, 1)
            
            print(f"DEBUG: Report data - interactions={len(interactions)}, overall_score={overall_score}, breakdown={score_breakdown}")
            
            # Generate PDF report
            report_path = generate_roleplay_report(
                user_name=user_name,
                user_email=user_email,
                roleplay_name=roleplay_name,
                scenario=scenario,
                overall_score=overall_score,
                score_breakdown=score_breakdown,
                interactions=interactions
            )
            
            # Send email with report
            success = send_report_email(
                to_email=user_email,
                user_name=user_name,
                roleplay_name=roleplay_name,
                overall_score=overall_score,
                report_pdf_path=report_path
            )
            
            cur.close()
            conn.close()
            
            print(f"Report {'sent successfully' if success else 'generation failed'} for play_id {play_id}")
            return success
            
        except Exception as e:
            print(f"Error in generate_and_send_report_async: {str(e)}")
            import traceback
            traceback.print_exc()
            return False


