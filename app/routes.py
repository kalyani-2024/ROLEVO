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
from app.queries import get_roleplay_file_path, old_query_showreport, get_play_info, query_create_chat_entry, query_create_score_master, query_create_score_breakdown, query_update, query_showreport, create_or_update, get_roleplays, get_roleplay, delete_roleplay, create_or_update_roleplay_config, get_roleplay_config, get_roleplay_with_config, create_cluster, get_clusters, get_cluster, add_roleplay_to_cluster, remove_roleplay_from_cluster, get_cluster_roleplays, delete_cluster
from gtts import gTTS
from dotenv import load_dotenv, find_dotenv
import uuid
import time
import requests
from werkzeug.security import generate_password_hash

load_dotenv(find_dotenv())
openai.api_key = os.getenv('OPENAI_API_KEY')

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
    final_json["start_time"] = play_info[1]
    final_json["user_id"] = play_info[2]
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
        
        # Create unique filename based on text content
        filename = f'speech_{hash(text)}.mp3'
        filepath = os.path.join(cache_dir, filename)
        
        # Check if audio file already exists in cache
        if not os.path.exists(filepath):
            try:
                tts = gTTS(text=text, lang='en', slow=False)
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
      return redirect(url_for('launch', user_id=1, roleplay_id=1))

@app.route("/launch/<int:user_id>/<string:roleplay_id>", methods=['GET', 'POST'])
def launch(user_id, roleplay_id):
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

@app.route("/chatbot/<string:roleplay_id>/<int:interaction_num>", methods=['GET', 'POST'])
def chatbot(roleplay_id, interaction_num):
    reader_obj = reader.excel.ExcelReader(session["exr_param0"], competency_descriptions, session["exr_param2"])
    interactor_obj = interface.interact.LLMInteractor(openai.api_key, reader_obj.get_system_prompt(), session['roleplay_id'])
    ai_obj = interface.openai.Conversation(reader_obj, interactor_obj)

    if roleplay_id == session['roleplay_id'] and interaction_num == session['interaction_number'] and session['user_id']:
        form = PostForm()
        resp = False
        if form.validate_on_submit():
            # Show thinking page immediately
            session['user_input'] = form.post.data.strip()
            return redirect(url_for('process_response'))

        # Rest of your existing chatbot code for displaying the form...
        context = {}
        context["scenario"] = reader_obj.get_system_prompt()
        context["image"] = reader_obj.get_system_prompt_image()
        context["cumul_score"] = cumul_score(roleplay_id)

        if 'comp_dialogue' in session:
            context["comp_dialogue"] = session["comp_dialogue"]
            context["last_round_result"] = session["last_round_result"]
            context["score"] = session["score"]
            context["image"] = reader_obj.get_images(session['image_interaction_number'])["images"][context["score"]-1]

        context["data"] = reader_obj.get_interaction(session['interaction_number'])
        if context["data"] == False:
            post_attempt_data(session['play_id'])
            return render_template("chatbot.html", context = context, form = form, final=True)
        else:
            if context["data"]["tip"] is not None:
                context["tip"] = context["data"]["tip"]

        return render_template("chatbot.html", context = context, form = form)
    else:
        return render_template('404.html', title='Error')

@app.route('/admin')
def admin():
    roleplays = get_roleplays()
    if roleplays is None:
        roleplays = []
    return render_template('admin.html', roleplays=roleplays)

@app.route('/adminview', defaults={'id': None}, methods=['GET'])
@app.route('/adminview/<string:id>', methods=['GET'])
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
        id = form['id']
        name = form['name']
        scenario = form['scenario']
        person_name = form['person_name']
    except Exception as e:
        flash("Missing required form fields.")
        return redirect(request.referrer or url_for('adminview'))

    roleplay_file_path = ''
    image_file_path = ''

    # Handle roleplay file upload
    if files.get("roleplay_file"):
        roleplay_file = f"{id}_{int(time.time())}_{files['roleplay_file'].filename}"
        roleplay_file_path = os.path.join(app.config['UPLOAD_PATH_ROLEPLAY'], roleplay_file)
        file_ext = os.path.splitext(roleplay_file)[1].lower()
        if file_ext not in [ext.lower() for ext in app.config['UPLOAD_EXTENSIONS_ROLEPLAY']]:
            flash("Invalid roleplay file extension.")
            return redirect(request.referrer or url_for('adminview'))
        files['roleplay_file'].save(roleplay_file_path)

    # Handle image file upload
    if files.get("image_file"):
        image_file = f"{id}_{int(time.time())}_{files['image_file'].filename}"
        image_file_path = os.path.join(app.config['UPLOAD_PATH_IMAGES'], image_file)
        file_ext = os.path.splitext(image_file)[1].lower()
        if file_ext not in [ext.lower() for ext in app.config['UPLOAD_EXTENSIONS_IMAGES']]:
            flash("Invalid image file extension.")
            return redirect(request.referrer or url_for('adminview'))
        files['image_file'].save(image_file_path)

    # Validate Excel files with enhanced validator that stores data in arrays
    validation_errors = []
    if roleplay_file_path and image_file_path:
        try:
            from app.enhanced_excel_validator import validate_excel_files_detailed
            is_valid, detailed_report, validation_data = validate_excel_files_detailed(roleplay_file_path, image_file_path)

            # DEBUG: Print validation results to console
            print(f"\n🔍 VALIDATION DEBUG:")
            print(f"   File paths: {roleplay_file_path}, {image_file_path}")
            print(f"   Is valid: {is_valid}")
            print(f"   Errors found: {len(validation_data.get('errors', []))}")
            print(f"   Warnings found: {len(validation_data.get('warnings', []))}")
            for error in validation_data.get('errors', []):
                print(f"   ERROR: {error}")
            print(f"🔍 END DEBUG\n")

            if not is_valid:
                # Delete uploaded files if validation fails
                if os.path.exists(roleplay_file_path):
                    os.remove(roleplay_file_path)
                if os.path.exists(image_file_path):
                    os.remove(image_file_path)

                # Check if this is a structural validation failure
                if "STRUCTURAL VALIDATION FAILED:" in detailed_report:
                    # Extract structural errors from detailed_report
                    structural_errors = detailed_report.split("STRUCTURAL VALIDATION FAILED:\n")[1].strip().split('\n')
                    
                    print(f"📢 FLASHING STRUCTURAL ERRORS: {len(structural_errors)} errors")
                    flash("❌ STRUCTURAL VALIDATION FAILED:")
                    flash("Excel file structure does not match required format.")
                    
                    for i, error in enumerate(structural_errors[:10]):  # Show first 10 structural errors
                        if error.strip():
                            error_msg = f"   • {error.strip()}"
                            flash(error_msg)
                            print(f"📢 FLASHED ERROR {i+1}: {error_msg}")
                    
                    if len(structural_errors) > 10:
                        flash(f"   ... and {len(structural_errors) - 10} more structural issues.")
                    
                    # Debug: Check if messages were actually flashed
                    from flask import session
                    print(f"🔍 SESSION AFTER FLASHING: {dict(session)}")
                    print(f"🔍 SESSION FLASH KEY: {session.get('_flashes', 'NOT FOUND')}")
                    
                    # Try to get flashed messages to see if they exist
                    from flask import get_flashed_messages
                    test_messages = get_flashed_messages(with_categories=True)
                    print(f"🔍 GET_FLASHED_MESSAGES TEST: {test_messages}")
                    
                    # Re-flash them if they were consumed
                    if test_messages:
                        for category, message in test_messages:
                            flash(message, category)
                        print(f"🔄 RE-FLASHED {len(test_messages)} MESSAGES")
                    
                    print(f"📢 TOTAL FLASH MESSAGES SENT: {len(structural_errors[:10]) + 2}")
                
                else:
                    # Handle content validation errors
                    flash("Excel file validation failed with detailed analysis:")
                    
                    # Show only critical errors - no improvement suggestions
                    errors = validation_data.get('errors', [])
                    
                    if errors:
                        flash(f"❌ Missing Data Found ({len(errors)}) - Must be fixed:")
                        for error in errors[:15]:  # Show more errors since we removed warnings
                            flash(f"   • {error}")
                        if len(errors) > 15:
                            flash(f"   ... and {len(errors) - 15} more missing data issues. Check console for full report.")
                
                # Print full detailed report to console for developer debugging
                print("\n" + "="*80)
                print("FULL EXCEL VALIDATION REPORT:")
                print("="*80)
                print(detailed_report)
                print("="*80 + "\n")
                
                # Instead of redirect, render template directly to preserve flash messages
                return render_template('adminview.html', roleplay=None, config=None)
            else:
                # Show success message with data summary - no improvement suggestions
                roleplay_interactions = len(validation_data.get('roleplay_data', []))
                image_interactions = len(validation_data.get('image_data', []))
                
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
        files['comp_file'].save(comp_file_path)

    # Handle ideal video upload
    ideal_video_path = ''
    if files.get("ideal_video"):
        ideal_video_file = f"{id}_{int(time.time())}_{files['ideal_video'].filename}"
        ideal_video_path = os.path.join(app.config['UPLOAD_PATH_IMAGES'], ideal_video_file)  # Using images folder for videos too
        file_ext = os.path.splitext(ideal_video_file)[1].lower()
        if file_ext not in ['.mp4', '.avi', '.mov', '.wmv']:
            flash("Invalid video file extension. Please use mp4, avi, mov, or wmv.")
            return redirect(request.referrer or url_for('adminview'))
        files['ideal_video'].save(ideal_video_path)

    # Save to database
    new_id = create_or_update(id, name, person_name, scenario, roleplay_file_path, image_file_path)
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
            'voice_assessment_enabled': form.get('voice_assessment_enabled') == 'on'
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
        roleplay_file_path = os.path.join(app.config['UPLOAD_PATH_ROLEPLAY'], roleplay_file)
        file_ext = os.path.splitext(roleplay_file)[1]
        if file_ext not in app.config['UPLOAD_EXTENSIONS_ROLEPLAY']:
            abort(400)
        files['roleplay_file'].save(roleplay_file_path)
    if files.get("image_file"):
        image_file = str(id) + "_" + str(int(time.time())) + "_" + str(files['image_file'].filename)
        image_file_path = os.path.join(app.config['UPLOAD_PATH_IMAGES'], image_file)
        file_ext = os.path.splitext(image_file)[1]
        if file_ext not in app.config['UPLOAD_EXTENSIONS_IMAGES']:
            abort(400)
        files['image_file'].save(image_file_path)
    if files.get("comp_file"):
        comp_file_path = os.path.join(app.config['UPLOAD_PATH_COMP'], 'Competency descriptions.xlsx')
        file_ext = os.path.splitext(files['comp_file'].filename)[1]
        if file_ext not in app.config['UPLOAD_EXTENSIONS_COMP']:
            abort(400)
        files['comp_file'].save(comp_file_path)
    id = create_or_update(id, name, person_name, scenario, roleplay_file_path, image_file_path)
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
def admin_clusters():
    """Display all clusters"""
    clusters = get_clusters()
    if clusters is None:
        clusters = []
    return render_template('admin_clusters.html', clusters=clusters)

@app.route('/admin/clusters/new', methods=['GET'])
def admin_cluster_new():
    """Show form to create new cluster"""
    roleplays = get_roleplays()
    if roleplays is None:
        roleplays = []
    return render_template('admin_cluster_form.html', cluster=None, roleplays=roleplays)

@app.route('/admin/clusters/<int:cluster_id>/edit', methods=['GET'])
def admin_cluster_edit(cluster_id):
    """Show form to edit cluster"""
    cluster = get_cluster(cluster_id)
    if not cluster:
        flash('Cluster not found')
        return redirect(url_for('admin_clusters'))
    
    roleplays = get_roleplays()
    cluster_roleplays = get_cluster_roleplays(cluster_id)
    
    return render_template('admin_cluster_form.html', 
                         cluster=cluster, 
                         roleplays=roleplays, 
                         cluster_roleplays=cluster_roleplays)

@app.route('/admin/clusters', methods=['POST'])
def admin_cluster_create():
    """Create or update cluster"""
    try:
        form_data = request.form.to_dict()
        cluster_id = form_data.get('cluster_id')
        
        if cluster_id:  # Edit existing cluster
            # Update cluster details would go here
            # For now, just handle roleplay assignments
            pass
        else:  # Create new cluster
            new_cluster_id = create_cluster(
                name=form_data['name'],
                cluster_id=None,  # Auto-generate cluster ID
                cluster_type=form_data['type']
            )
            
            if new_cluster_id:
                # Add selected roleplays to cluster
                selected_roleplays = request.form.getlist('selected_roleplays')
                for idx, roleplay_id in enumerate(selected_roleplays):
                    add_roleplay_to_cluster(new_cluster_id, roleplay_id, idx + 1)
                
                flash('Cluster created successfully!')
            else:
                flash('Failed to create cluster')
        
        return redirect(url_for('admin_clusters'))
        
    except Exception as e:
        print(f"Error creating cluster: {str(e)}")
        flash('Error creating cluster')
        return redirect(url_for('admin_clusters'))

@app.route('/admin/clusters/<int:cluster_id>/delete', methods=['GET'])
def admin_cluster_delete(cluster_id):
    """Delete cluster"""
    if delete_cluster(cluster_id):
        flash('Cluster deleted successfully!')
    else:
        flash('Failed to delete cluster')
    return redirect(url_for('admin_clusters'))

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
