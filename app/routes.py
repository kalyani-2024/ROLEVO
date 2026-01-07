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
import datetime
from app.queries import get_roleplay_file_path, old_query_showreport, get_play_info, query_create_chat_entry, query_create_score_master, query_create_score_breakdown, query_update, query_showreport, create_or_update, get_roleplays, get_roleplay, delete_roleplay, create_or_update_roleplay_config, get_roleplay_config, get_roleplay_with_config, create_cluster, update_cluster, get_clusters, get_cluster, add_roleplay_to_cluster, remove_roleplay_from_cluster, get_cluster_roleplays, delete_cluster, get_all_users, get_user, assign_cluster_to_user, remove_cluster_from_user, get_user_clusters, get_cluster_users, get_user_id, create_user_account, get_user_by_email, create_user, validate_password, get_16pf_config_for_roleplay, save_16pf_analysis_result, update_16pf_analysis_result, get_16pf_analysis_by_play_id
from gtts import gTTS
from deep_translator import GoogleTranslator
from dotenv import load_dotenv, find_dotenv
import uuid
import time
import requests
from werkzeug.security import generate_password_hash
from functools import wraps
from app.report_generator_v2 import generate_roleplay_report
from app.email_service import send_report_email
from app.persona360_service import get_persona360_service, analyze_audio_for_16pf

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
    
    # Trigger 16PF voice analysis if enabled for this roleplay
    try:
        roleplay_id = play_info[3] if play_info else None
        if roleplay_id:
            trigger_16pf_analysis_if_enabled(play_id, user_id, roleplay_id)
    except Exception as e:
        print(f"Error triggering 16PF analysis: {str(e)}")


def merge_audio_files_for_play(play_id):
    """Merge all user audio recordings for a play session into a single file.
    
    Returns the path to the merged audio file, or None if no files to merge.
    """
    try:
        user_recordings_dir = os.path.join(app.root_path, 'static', 'user_recordings')
        if not os.path.exists(user_recordings_dir):
            print(f"[16PF] User recordings directory does not exist")
            return None
        
        # Find all audio files for this play_id
        audio_files = []
        for filename in os.listdir(user_recordings_dir):
            if filename.endswith(('.webm', '.mp3', '.wav', '.m4a', '.ogg')):
                if f'play{play_id}_' in filename:
                    file_path = os.path.join(user_recordings_dir, filename)
                    # Get modification time for sorting
                    audio_files.append((file_path, os.path.getmtime(file_path)))
        
        if not audio_files:
            print(f"[16PF] No audio files found for play_id {play_id}")
            return None
        
        if len(audio_files) == 1:
            # Only one file, no need to merge
            print(f"[16PF] Single audio file found: {audio_files[0][0]}")
            return audio_files[0][0]
        
        # Sort by modification time (oldest first)
        audio_files.sort(key=lambda x: x[1])
        file_paths = [f[0] for f in audio_files]
        
        print(f"[16PF] Found {len(file_paths)} audio files to merge for play_id {play_id}")
        for i, fp in enumerate(file_paths):
            print(f"[16PF]   {i+1}. {os.path.basename(fp)}")
        
        # Create merged audio directory
        merged_dir = os.path.join(app.root_path, 'static', 'merged_audio')
        os.makedirs(merged_dir, exist_ok=True)
        
        merged_filename = f"merged_play{play_id}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
        merged_path = os.path.join(merged_dir, merged_filename)
        
        # ===== METHOD 1: Use pydub (Python-based, no external dependencies) =====
        try:
            from pydub import AudioSegment
            
            print(f"[16PF] Merging audio files using pydub...")
            
            # Combine all audio files
            combined = None
            for i, fp in enumerate(file_paths):
                try:
                    # Load audio file (pydub auto-detects format)
                    if fp.endswith('.webm'):
                        # For webm, we need to specify format
                        audio = AudioSegment.from_file(fp, format="webm")
                    elif fp.endswith('.mp3'):
                        audio = AudioSegment.from_mp3(fp)
                    elif fp.endswith('.wav'):
                        audio = AudioSegment.from_wav(fp)
                    else:
                        audio = AudioSegment.from_file(fp)
                    
                    if combined is None:
                        combined = audio
                    else:
                        # Add a small silence between segments (300ms)
                        silence = AudioSegment.silent(duration=300)
                        combined = combined + silence + audio
                    
                    print(f"[16PF]   Added segment {i+1}: {os.path.basename(fp)} ({len(audio)}ms)")
                except Exception as seg_error:
                    print(f"[16PF]   Warning: Could not load {os.path.basename(fp)}: {seg_error}")
                    continue
            
            if combined is not None and len(combined) > 0:
                # Export as MP3
                combined.export(merged_path, format="mp3")
                print(f"[16PF] Successfully merged {len(file_paths)} files into: {merged_path}")
                print(f"[16PF] Total duration: {len(combined) / 1000:.1f} seconds")
                return merged_path
            else:
                print(f"[16PF] pydub: No audio segments could be combined")
                
        except ImportError:
            print(f"[16PF] pydub not installed, trying ffmpeg...")
        except Exception as pydub_error:
            print(f"[16PF] pydub merge failed: {pydub_error}, trying ffmpeg...")
        
        # ===== METHOD 2: Use ffmpeg if available =====
        try:
            import subprocess
            
            # Create a file list for ffmpeg concat
            list_file = os.path.join(merged_dir, f"filelist_{play_id}.txt")
            with open(list_file, 'w') as f:
                for fp in file_paths:
                    # Escape path for ffmpeg
                    escaped_path = fp.replace("'", "'\\''")
                    f.write(f"file '{escaped_path}'\n")
            
            # Run ffmpeg to concatenate
            result = subprocess.run([
                'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
                '-i', list_file, '-c', 'copy', merged_path.replace('.mp3', '.webm')
            ], capture_output=True, text=True, timeout=60)
            
            # Clean up list file
            try:
                os.remove(list_file)
            except:
                pass
            
            merged_webm = merged_path.replace('.mp3', '.webm')
            if result.returncode == 0 and os.path.exists(merged_webm):
                print(f"[16PF] Successfully merged audio files with ffmpeg: {merged_webm}")
                return merged_webm
            else:
                print(f"[16PF] ffmpeg merge failed: {result.stderr}")
        except FileNotFoundError:
            print("[16PF] ffmpeg not found")
        except Exception as e:
            print(f"[16PF] ffmpeg error: {e}")
        
        # ===== FALLBACK: Concatenate raw bytes (basic, may have audio glitches) =====
        try:
            print(f"[16PF] Using fallback: concatenating raw audio bytes...")
            
            # Just concatenate the webm files (works for same-format files)
            fallback_path = os.path.join(merged_dir, f"merged_play{play_id}_raw.webm")
            with open(fallback_path, 'wb') as outfile:
                for i, fp in enumerate(file_paths):
                    with open(fp, 'rb') as infile:
                        outfile.write(infile.read())
            
            if os.path.exists(fallback_path) and os.path.getsize(fallback_path) > 0:
                print(f"[16PF] Created raw concatenated file: {fallback_path}")
                return fallback_path
        except Exception as raw_error:
            print(f"[16PF] Raw concatenation failed: {raw_error}")
        
        # Last resort: return the largest file
        largest_file = max(file_paths, key=lambda x: os.path.getsize(x))
        print(f"[16PF] Fallback: Using largest single audio file: {largest_file}")
        return largest_file
        
    except Exception as e:
        print(f"[16PF] Error in merge_audio_files_for_play: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def trigger_16pf_analysis_if_enabled(play_id, user_id, roleplay_id):
    """Check if 16PF analysis is enabled for this roleplay and trigger it if so."""
    try:
        # Get 16PF configuration for this roleplay
        pf16_config = get_16pf_config_for_roleplay(roleplay_id)
        
        if not pf16_config:
            print(f"[16PF] No config found for roleplay {roleplay_id}")
            return
        
        if not pf16_config.get('enable_16pf_analysis'):
            print(f"[16PF] Analysis disabled for roleplay {roleplay_id}")
            return
        
        analysis_source = pf16_config.get('pf16_analysis_source', 'none')
        if analysis_source == 'none':
            print(f"[16PF] Analysis source is 'none' for roleplay {roleplay_id}")
            return
        
        send_audio = pf16_config.get('pf16_send_audio_for_analysis', True)
        if not send_audio:
            print(f"[16PF] Audio sending disabled for roleplay {roleplay_id}")
            return
        
        print(f"[16PF] Triggering analysis for play_id={play_id}, source={analysis_source}")
        
        # Get user info for age/gender (from session or defaults)
        user_age = session.get('user_age', pf16_config.get('pf16_default_age', 30))
        user_gender = session.get('user_gender', 'Male')
        
        # First, try to merge all audio files from this play session
        merged_audio = merge_audio_files_for_play(play_id)
        
        # Find the audio file(s) for this play session
        audio_file_path = merged_audio or get_audio_file_for_play(play_id)
        
        if not audio_file_path:
            print(f"[16PF] No audio file found for play_id {play_id}")
            return
        
        # Create a pending analysis record
        analysis_id = save_16pf_analysis_result(
            play_id=play_id,
            user_id=user_id,
            roleplay_id=roleplay_id,
            audio_file_path=audio_file_path,
            user_age=user_age,
            user_gender=user_gender,
            analysis_source=analysis_source
        )
        
        if not analysis_id:
            print(f"[16PF] Failed to create analysis record")
            return
        
        # Run analysis in background thread
        thread = threading.Thread(
            target=run_16pf_analysis_async,
            args=(analysis_id, audio_file_path, user_age, user_gender, analysis_source)
        )
        thread.daemon = True
        thread.start()
        print(f"[16PF] Started background analysis thread for analysis_id {analysis_id}")
        
    except Exception as e:
        print(f"[16PF] Error in trigger_16pf_analysis_if_enabled: {str(e)}")


def get_audio_file_for_play(play_id):
    """Find the audio recording file for a specific play session.
    
    This function looks for recorded audio files associated with the play session.
    Priority: user_recordings > audio_cache > other locations
    """
    try:
        # PRIORITY 1: Check user recordings directory first (actual user voice recordings)
        user_recordings_dir = os.path.join(app.root_path, 'static', 'user_recordings')
        if os.path.exists(user_recordings_dir):
            # Get all files for this play_id, sorted by modification time (newest first)
            matching_files = []
            for filename in os.listdir(user_recordings_dir):
                if filename.endswith(('.webm', '.mp3', '.wav', '.m4a', '.ogg')):
                    if f'play{play_id}_' in filename or f'play_{play_id}' in filename:
                        file_path = os.path.join(user_recordings_dir, filename)
                        matching_files.append((file_path, os.path.getmtime(file_path)))
            
            if matching_files:
                # Return the most recent file
                matching_files.sort(key=lambda x: x[1], reverse=True)
                print(f"[16PF] Found user recording: {matching_files[0][0]}")
                return matching_files[0][0]
        
        # PRIORITY 2: Check for concatenated/merged audio files for this play
        merged_audio_dir = os.path.join(app.root_path, 'static', 'merged_audio')
        if os.path.exists(merged_audio_dir):
            for filename in os.listdir(merged_audio_dir):
                if filename.endswith(('.webm', '.mp3', '.wav', '.m4a', '.ogg')):
                    if f'play{play_id}' in filename or f'play_{play_id}' in filename:
                        return os.path.join(merged_audio_dir, filename)
        
        # PRIORITY 3: Check other common locations for audio files
        audio_dirs = [
            os.path.join(app.root_path, 'temp'),
            os.path.join(os.path.dirname(app.root_path), 'uploads'),
        ]
        
        # Look for files with play_id in the name
        for audio_dir in audio_dirs:
            if not os.path.exists(audio_dir):
                continue
            
            for filename in os.listdir(audio_dir):
                # Check for audio/video files
                if filename.endswith(('.mp3', '.wav', '.mp4', '.m4a', '.webm', '.ogg')):
                    # Check if play_id is in filename
                    if str(play_id) in filename or f'play_{play_id}' in filename:
                        return os.path.join(audio_dir, filename)
        
        # PRIORITY 4: Check chathistory table for audio_file_path
        import mysql.connector as ms
        from dotenv import load_dotenv
        load_dotenv()
        
        host = os.getenv('DB_HOST', 'localhost')
        user = os.getenv('DB_USER', 'root')
        password = os.getenv('DB_PASSWORD')
        database = os.getenv('DB_NAME', 'roleplay')
        
        with ms.connect(host=host, user=user, password=password, database=database) as dbconn:
            cursor = dbconn.cursor()
            cursor.execute("""
                SELECT ch.audio_file_path 
                FROM chathistory ch
                JOIN scoremaster sm ON ch.id = sm.chathistory_id
                WHERE sm.play_id = %s AND ch.audio_file_path IS NOT NULL AND ch.audio_file_path != ''
                LIMIT 1
            """, (play_id,))
            result = cursor.fetchone()
            if result and result[0]:
                audio_path = result[0]
                if os.path.exists(audio_path):
                    return audio_path
        
        return None
        
    except Exception as e:
        print(f"[16PF] Error finding audio file for play {play_id}: {str(e)}")
        return None


def run_16pf_analysis_async(analysis_id, audio_file_path, user_age, user_gender, analysis_source):
    """Run 16PF analysis in background and update the database with results."""
    try:
        print(f"[16PF] Starting analysis for analysis_id={analysis_id}")
        
        # Update status to processing
        update_16pf_analysis_result(analysis_id, status='processing')
        
        if analysis_source == 'persona360':
            # Use Persona360 API
            success, result = analyze_audio_for_16pf(
                file_path=audio_file_path,
                age=user_age,
                gender=user_gender
            )
            
            if success:
                update_16pf_analysis_result(
                    analysis_id=analysis_id,
                    status='completed',
                    raw_response=result.get('raw_response'),
                    personality_scores=result.get('personality_scores'),
                    composite_scores=result.get('composite_scores'),
                    overall_role_fit=result.get('overall_role_fit'),
                    analysis_confidence=result.get('analysis_confidence')
                )
                print(f"[16PF] Analysis completed successfully for analysis_id={analysis_id}")
            else:
                error_msg = result.get('error', 'Unknown error')
                update_16pf_analysis_result(
                    analysis_id=analysis_id,
                    status='failed',
                    error_message=error_msg
                )
                print(f"[16PF] Analysis failed for analysis_id={analysis_id}: {error_msg}")
        
        elif analysis_source == 'third_party':
            # Placeholder for third-party plugin integration
            # This would be implemented based on the specific third-party API
            update_16pf_analysis_result(
                analysis_id=analysis_id,
                status='failed',
                error_message='Third-party plugin not yet implemented'
            )
            print(f"[16PF] Third-party plugin not implemented yet")
        
        else:
            update_16pf_analysis_result(
                analysis_id=analysis_id,
                status='failed',
                error_message=f'Unknown analysis source: {analysis_source}'
            )
            
    except Exception as e:
        error_msg = str(e)
        print(f"[16PF] Error in async analysis: {error_msg}")
        try:
            update_16pf_analysis_result(
                analysis_id=analysis_id,
                status='failed',
                error_message=error_msg
            )
        except:
            pass


@app.route("/api/upload-user-audio", methods=['POST'])
def upload_user_audio():
    """
    Upload user's recorded audio for 16PF analysis.
    This is called from the chatbot page when the user records their voice.
    The audio is saved and associated with the current play session.
    """
    try:
        if 'audio' not in request.files:
            return jsonify({"success": False, "error": "No audio file provided"}), 400
        
        audio_file = request.files['audio']
        play_id = request.form.get('play_id', session.get('play_id', ''))
        interaction_num = request.form.get('interaction_number', '1')
        
        if not play_id:
            return jsonify({"success": False, "error": "No play_id available"}), 400
        
        # Create directory for user recordings
        recordings_dir = os.path.join(app.root_path, 'static', 'user_recordings')
        os.makedirs(recordings_dir, exist_ok=True)
        
        # Generate unique filename
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"user_audio_play{play_id}_int{interaction_num}_{timestamp}.webm"
        file_path = os.path.join(recordings_dir, filename)
        
        # Save the audio file
        audio_file.save(file_path)
        print(f"[16PF] Saved user audio: {file_path}")
        
        # Store the path in session for later use by 16PF analysis
        if 'user_audio_files' not in session:
            session['user_audio_files'] = []
        session['user_audio_files'].append(file_path)
        session.modified = True
        
        # Also store as the main audio file for this play session
        session['current_user_audio'] = file_path
        
        return jsonify({
            "success": True,
            "audio_path": file_path,
            "message": "Audio uploaded successfully"
        })
        
    except Exception as e:
        print(f"[16PF] Error uploading user audio: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


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
            print("❌ AUDIO ERROR: No text provided")
            return "No text provided", 400

        # Create cache directory
        cache_dir = os.path.join(app.root_path, 'static', 'audio_cache')
        os.makedirs(cache_dir, exist_ok=True)
        
        # Get selected language from session, default to English
        selected_language = session.get('selected_language', 'English')
        
        # Get gender/character preference (default to female for backward compatibility)
        gender = request.args.get('gender', 'female').lower()
        character = request.args.get('character', '').strip()
        
        print(f"🔊 AUDIO REQUEST: text='{text[:50]}...', gender={gender}, character={character}, lang={selected_language}")
        
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
        
        # Determine TLD (top-level domain) for voice gender
        # gTTS uses different TLDs for different regional voices
        # Note: gTTS doesn't have true gender voices, but different regions have different pitch/tone
        tld = 'com'  # Default
        slow = False  # Speech rate
        
        # Gender-based voice selection using regional variants and speech rate
        # Using only reliable TLDs that Google supports
        if gender == 'male':
            # Male voices: Use TLDs that are reliable and have deeper tone
            if lang_code == 'en':
                tld = 'co.in'  # Indian English (deeper, clearer)
                slow = False
            elif lang_code == 'hi':
                tld = 'co.in'  # Indian Hindi
                slow = False
            else:
                tld = 'com'
                slow = False
        else:  # female (default)
            # Female voices: Use standard TLDs
            if lang_code == 'en':
                tld = 'com'  # US English (standard)
                slow = False
            elif lang_code == 'hi':
                tld = 'co.in'  # Indian Hindi
                slow = False
            else:
                tld = 'com'
                slow = False
        
        print(f"🎤 Voice config: gender={gender}, tld={tld}, slow={slow}")
        
        # Create unique filename based on text content, language, and gender/character
        # Use a safer hash to avoid negative numbers
        text_hash = abs(hash(text)) % (10 ** 10)
        # Include gender and character in filename for proper caching
        gender_char = f"{gender}_{character}" if character else gender
        filename = f'speech_{text_hash}_{lang_code}_{gender_char}.mp3'
        filepath = os.path.join(cache_dir, filename)
        
        print(f"Audio request: lang={selected_language}, cached={os.path.exists(filepath)}, file={filename}")
        
        # Check if audio file already exists in cache
        if not os.path.exists(filepath):
            try:
                print(f"Generating new audio for: {text[:50]}...")
                
                # Add timeout to gTTS generation (max 10 seconds)
                import signal
                
                def timeout_handler(signum, frame):
                    raise TimeoutError("Audio generation timeout")
                
                # Set timeout for Windows (use threading for cross-platform compatibility)
                import threading
                
                generation_error = None
                tts_method_used = None
                
                def generate_tts():
                    nonlocal generation_error, tts_method_used
                    
                    # TTS Priority:
                    # 1. Edge-TTS (online, high quality, many voices)
                    # 2. pyttsx3 (offline, reliable, supports gender) - fallback
                    # 3. gTTS (online, basic) - final fallback
                    
                    # ===== ATTEMPT 1: Edge-TTS (Online - High Quality) =====
                    try:
                        import edge_tts
                        import asyncio
                    except ImportError as ie:
                        print(f"⚠️ edge-tts not installed, skipping to pyttsx3")
                        edge_tts = None
                    
                    if edge_tts:
                        try:
                            # Character-to-voice mapping (for team roleplays with multiple speakers)
                            character_hash = hash(character.lower()) if character else 0
                            
                            # Microsoft Edge TTS voices - works on all platforms
                            male_voices = [
                                'en-US-GuyNeural',
                                'en-US-ChristopherNeural',
                                'en-US-EricNeural',
                                'en-GB-RyanNeural',
                                'en-AU-WilliamNeural',
                                'en-IN-PrabhatNeural',
                            ]
                            
                            female_voices = [
                                'en-US-JennyNeural',
                                'en-US-AriaNeural',
                                'en-US-SaraNeural',
                                'en-GB-SoniaNeural',
                                'en-AU-NatashaNeural',
                                'en-IN-NeerjaNeural',
                            ]
                            
                            # Non-English voices
                            if lang_code == 'hi':
                                male_voices = ['hi-IN-MadhurNeural']
                                female_voices = ['hi-IN-SwaraNeural']
                            elif lang_code == 'ta':
                                male_voices = ['ta-IN-ValluvarNeural']
                                female_voices = ['ta-IN-PallaviNeural']
                            elif lang_code == 'te':
                                male_voices = ['te-IN-MohanNeural']
                                female_voices = ['te-IN-ShrutiNeural']
                            elif lang_code == 'kn':
                                male_voices = ['kn-IN-GaganNeural']
                                female_voices = ['kn-IN-SapnaNeural']
                            elif lang_code == 'mr':
                                male_voices = ['mr-IN-ManoharNeural']
                                female_voices = ['mr-IN-AarohiNeural']
                            elif lang_code == 'bn':
                                male_voices = ['bn-IN-BashkarNeural']
                                female_voices = ['bn-IN-TanishaaNeural']
                            elif lang_code == 'gu':
                                male_voices = ['gu-IN-NiranjanNeural']
                                female_voices = ['gu-IN-DhwaniNeural']
                            elif lang_code == 'ml':
                                male_voices = ['ml-IN-MidhunNeural']
                                female_voices = ['ml-IN-SobhanaNeural']
                            elif lang_code == 'fr':
                                male_voices = ['fr-FR-HenriNeural', 'fr-FR-AlainNeural']
                                female_voices = ['fr-FR-DeniseNeural', 'fr-FR-EloiseNeural']
                            elif lang_code == 'ar':
                                male_voices = ['ar-SA-HamedNeural']
                                female_voices = ['ar-SA-ZariyahNeural']
                            
                            # Select voice based on gender and character
                            if gender == 'male':
                                voice_index = abs(character_hash) % len(male_voices)
                                selected_voice = male_voices[voice_index]
                            else:
                                voice_index = abs(character_hash) % len(female_voices)
                                selected_voice = female_voices[voice_index]
                            
                            print(f"🎙️ Edge-TTS: Trying {gender.upper()} voice: {selected_voice}")
                            
                            # Generate audio using edge-tts with retry
                            async def generate_edge_audio():
                                max_retries = 2
                                for attempt in range(max_retries):
                                    try:
                                        communicate = edge_tts.Communicate(text, selected_voice)
                                        await communicate.save(filepath)
                                        return True
                                    except Exception as e:
                                        if attempt < max_retries - 1:
                                            print(f"⚠️ Edge-TTS attempt {attempt + 1} failed: {str(e)}")
                                            await asyncio.sleep(0.3)
                                        else:
                                            raise e
                                return False
                            
                            # Run async
                            try:
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                loop.run_until_complete(generate_edge_audio())
                                loop.close()
                            except RuntimeError:
                                asyncio.run(generate_edge_audio())
                            
                            if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                                tts_method_used = 'edge-tts'
                                print(f"✅ Audio generated with Edge-TTS ({selected_voice}): {filename}")
                                return  # Success!
                            else:
                                print(f"⚠️ Edge-TTS created empty/no file, trying pyttsx3...")
                                
                        except Exception as edge_error:
                            print(f"⚠️ Edge-TTS failed: {str(edge_error)}, trying pyttsx3...")
                    
                    # ===== ATTEMPT 2: pyttsx3 (Offline - Reliable Fallback) =====
                    if lang_code == 'en':
                        try:
                            import pyttsx3
                            
                            engine = pyttsx3.init()
                            voices = engine.getProperty('voices')
                            
                            # Find male and female voices
                            male_voice = None
                            female_voice = None
                            for voice in voices:
                                voice_name = voice.name.lower()
                                if 'david' in voice_name or 'male' in voice_name:
                                    male_voice = voice.id
                                elif 'zira' in voice_name or 'female' in voice_name:
                                    female_voice = voice.id
                            
                            # Select voice based on gender
                            if gender == 'male' and male_voice:
                                engine.setProperty('voice', male_voice)
                                print(f"🎙️ pyttsx3: Using MALE voice (David)")
                            elif gender == 'female' and female_voice:
                                engine.setProperty('voice', female_voice)
                                print(f"🎙️ pyttsx3: Using FEMALE voice (Zira)")
                            elif voices:
                                # Fallback to first available voice
                                engine.setProperty('voice', voices[0].id)
                                print(f"🎙️ pyttsx3: Using default voice {voices[0].name}")
                            
                            # Add voice variation for different characters (pitch and rate)
                            base_rate = 180  # Normal speech rate
                            base_volume = 1.0
                            
                            if character:
                                char_hash = abs(hash(character.lower()))
                                # Vary rate between 150-210 (slower to faster)
                                rate_variation = (char_hash % 60) + 150
                                engine.setProperty('rate', rate_variation)
                                print(f"🎭 Character '{character}': rate={rate_variation}")
                            else:
                                engine.setProperty('rate', base_rate)
                            
                            engine.setProperty('volume', base_volume)
                            
                            # Save to file
                            engine.save_to_file(text, filepath)
                            engine.runAndWait()
                            engine.stop()
                            
                            if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                                tts_method_used = 'pyttsx3'
                                print(f"✅ Audio generated with pyttsx3 ({gender}): {filename}")
                                return  # Success!
                            else:
                                print(f"⚠️ pyttsx3 created empty file, trying gTTS...")
                                
                        except Exception as pyttsx3_error:
                            print(f"⚠️ pyttsx3 failed: {str(pyttsx3_error)}, trying gTTS...")
                    
                    # ===== ATTEMPT 3: gTTS (Final Fallback) =====
                    try:
                        from gtts import gTTS
                        
                        gtts_lang_map = {
                            'en': 'en', 'hi': 'hi', 'ta': 'ta', 'te': 'te',
                            'kn': 'kn', 'mr': 'mr', 'bn': 'bn', 'gu': 'gu',
                            'ml': 'ml', 'fr': 'fr', 'ar': 'ar'
                        }
                        gtts_lang = gtts_lang_map.get(lang_code, 'en')
                        
                        tts = gTTS(text=text, lang=gtts_lang, slow=False)
                        tts.save(filepath)
                        
                        if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                            tts_method_used = 'gTTS'
                            print(f"✅ Audio generated with gTTS ({gtts_lang}): {filename}")
                            print(f"   Note: gTTS doesn't support gender/voice variation")
                            return  # Success!
                            
                    except Exception as gtts_error:
                        print(f"❌ gTTS also failed: {str(gtts_error)}")
                        generation_error = gtts_error
                
                # Run TTS generation in thread with timeout (15 seconds for fallback)
                tts_thread = threading.Thread(target=generate_tts)
                tts_thread.daemon = True
                tts_thread.start()
                tts_thread.join(timeout=15)  # 15 second timeout (allows time for fallback)
                
                if tts_thread.is_alive():
                    print(f"⚠️ TTS generation timed out after 15 seconds")
                    return "Audio generation timed out. Please try again.", 504
                
                if generation_error:
                    raise generation_error
                    
                if not os.path.exists(filepath):
                    print(f"❌ Audio file was not created: {filepath}")
                    return "Audio file generation failed", 500
                    
            except Exception as e:
                error_msg = str(e)
                print(f"❌ TTS Error: {error_msg}")
                
                # Check if this is a PythonAnywhere whitelist issue
                if 'api.msedgeservices.com' in error_msg or 'getaddrinfo failed' in error_msg:
                    print("⚠️ This appears to be a network connectivity issue.")
                    print("   Possible causes:")
                    print("   1. PythonAnywhere free accounts have restricted external access")
                    print("   2. api.msedgeservices.com is not on the whitelist")
                    print("   3. Firewall blocking the connection")
                    print("   Solution: Using gTTS fallback or upgrade PythonAnywhere account")
                
                # Return a more user-friendly error
                if 'timeout' in error_msg.lower():
                    return "Audio generation is taking too long. Please try again.", 504
                elif 'network' in error_msg.lower() or 'connection' in error_msg.lower() or 'getaddrinfo' in error_msg:
                    return "Network error. Audio generation fallback activated.", 503
                else:
                    return f"Audio generation failed: {error_msg}", 500
        else:
            print(f"✅ Serving cached audio: {filename}")
        
        # Return cached file
        return send_file(
            filepath,
            mimetype="audio/mpeg",
            conditional=True,
            etag=True,
            max_age=3600  # Cache for 1 hour
        )
        
    except Exception as e:
        print(f"❌ Audio generation error: {str(e)}")
        import traceback
        traceback.print_exc()
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
        
        # Validate password against policy
        is_valid, error_message = validate_password(password)
        if not is_valid:
            flash(error_message)
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

        # Get roleplay data including competency file path
        cur.execute("""
            SELECT file_path, scenario, image_file_path, competency_file_path
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

        print(f"\n{'='*80}")
        print(f"🚀 LAUNCH ROUTE - Cluster ID Capture")
        print(f"{'='*80}")
        print(f"📋 Request Parameters:")
        print(f"   cluster_id from URL (raw): '{request.args.get('cluster_id')}'")
        print(f"   cluster_id (parsed as int): {cluster_id}")
        print(f"   selected_language: {selected_language}")
        print(f"   Full request.args: {dict(request.args)}")
        
        # If cluster_id is not in URL or is empty, try to get it from user_cluster table
        if cluster_id is None:
            print(f"\n⚠️  WARNING: No cluster_id in URL, querying user_cluster table")
            cur.execute("""
                SELECT cluster_id FROM user_cluster 
                WHERE user_id = %s 
                LIMIT 1
            """, (user_id,))
            result = cur.fetchone()
            if result:
                cluster_id = result[0]
                print(f"   Found cluster_id from user_cluster: {cluster_id}")
                print(f"   ⚠️  WARNING: Using LIMIT 1 - may not be correct cluster!")
            else:
                print(f"   ❌ No cluster found for user {user_id}")
        else:
            print(f"   ✅ cluster_id successfully captured from URL")
        
        print(f"{'='*80}\n")

        excel_path = resolve_file_path(roleplay_data[0], [app.config.get('UPLOAD_PATH_ROLEPLAY')])
        image_excel_path = resolve_file_path(roleplay_data[2], [app.config.get('UPLOAD_PATH_IMAGES')])
        
        # Load competency file for THIS specific roleplay
        competency_file_path = roleplay_data[3]  # Index 3 is competency_file_path
        roleplay_competencies = {}
        
        if competency_file_path:
            # Try to resolve the competency file path
            resolved_comp_path = resolve_file_path(competency_file_path, [app.config.get('UPLOAD_PATH_COMP')])
            if resolved_comp_path and os.path.exists(resolved_comp_path):
                try:
                    master_obj = reader.master.MasterLoader(resolved_comp_path)
                    roleplay_competencies = master_obj.get_competencies_as_list()
                    print(f"✅ Loaded competencies from roleplay-specific file: {resolved_comp_path}")
                except Exception as e:
                    print(f"⚠️ Error loading roleplay competency file: {e}")
                    roleplay_competencies = competency_descriptions  # Fallback to global
            else:
                print(f"⚠️ Competency file not found: {competency_file_path}, using global fallback")
                roleplay_competencies = competency_descriptions
        else:
            # No specific competency file, use global default
            print(f"ℹ️ No specific competency file for roleplay {roleplay_id}, using global fallback")
            roleplay_competencies = competency_descriptions

        print(f"Excel path: {excel_path}")
        print(f"Image Excel path: {image_excel_path}")
        print(f"Competency file: {competency_file_path if competency_file_path else 'Using global'}")
        print(f"Selected language: {selected_language}")

        # Get roleplay configuration for voice settings
        roleplay_config = get_roleplay_with_config(roleplay_id)
        input_type = 'audio'  # Always enable audio for scenario reading
        available_languages = 'English'  # Default
        max_interaction_time = 300  # Default 5 minutes
        max_total_time = 1800  # Default 30 minutes
        
        if roleplay_config and len(roleplay_config) > 11:
            # Roleplay table has 11 columns (0-10), config columns start at 11
            # Index 11 is input_type from the query in get_roleplay_with_config
            # Always use 'audio' to ensure scenario is read out loud
            input_type = 'audio'
            # Index 13 is available_languages
            available_languages = roleplay_config[13] if roleplay_config[13] else 'English'
            # Index 14 is max_interaction_time
            max_interaction_time = roleplay_config[14] if roleplay_config[14] else 300
            # Index 15 is max_total_time
            max_total_time = roleplay_config[15] if roleplay_config[15] else 1800
        
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
            'exr_competency_file': competency_file_path,  # Store only file path, not entire dict
            'roleplay_start_time': time.time()  # Store start time for total timer
        })
        
        print(f"\n💾 Session initialized:")
        print(f"   cluster_id stored in session: {cluster_id}")
        print(f"   roleplay_id: {roleplay_id}")
        print(f"   user_id: {user_id}")
        print(f"{'='*80}\n")

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

        # Initialize reader with roleplay-specific competencies
        try:
            reader_obj = reader.excel.ExcelReader(
                excel_path,
                roleplay_competencies,  # Use roleplay-specific competencies
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

def get_roleplay_competencies():
    """Helper function to load competencies from file path stored in session"""
    competency_file_path = session.get('exr_competency_file')
    
    if competency_file_path:
        resolved_comp_path = resolve_file_path(competency_file_path, [app.config.get('UPLOAD_PATH_COMP')])
        if resolved_comp_path and os.path.exists(resolved_comp_path):
            try:
                master_obj = reader.master.MasterLoader(resolved_comp_path)
                return master_obj.get_competencies_as_list()
            except Exception as e:
                print(f"Error loading competencies from {resolved_comp_path}: {e}")
    
    # Fallback to global competencies
    return competency_descriptions

@app.route("/chatbot/<path:roleplay_id>/<signed_int:interaction_num>", methods=['GET', 'POST'])

def chatbot(roleplay_id, interaction_num):
    # Load competencies from file path (not stored in session anymore)
    roleplay_competencies = get_roleplay_competencies()
    
    reader_obj = reader.excel.ExcelReader(session["exr_param0"], roleplay_competencies, session["exr_param2"])
    interactor_obj = interface.interact.LLMInteractor(openai.api_key, reader_obj.get_system_prompt(), session['roleplay_id'])
    ai_obj = interface.openai.Conversation(reader_obj, interactor_obj)

    # Special handling for completion (interaction_num = -1)
    # Update session interaction_number to match URL parameter for completion flow
    if interaction_num == -1 and roleplay_id == session.get('roleplay_id'):
        session['interaction_number'] = -1
        print(f"🏁 Completion URL detected: Setting session interaction_number to -1")
    
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
        
        print(f"🖼️ DEBUG IMAGE: System prompt image URL = {context['image']}")
        
        # Set default gender for initial scenario audio (before any interaction)
        context["gender"] = "male"  # Default voice for scenario description
        context["character"] = ""
        context["dialogue_segments"] = []
        print(f"🎬 INITIAL SCENARIO: Set default gender=male for scenario audio")
        
        # Get cluster type from database - ALWAYS fetch fresh, don't cache
        cluster_type = 'training'  # Default
        cluster_id = session.get('cluster_id')
        user_id = session.get('user_id')
        
        print(f"\n{'='*80}")
        print(f"🔍 CLUSTER TYPE DEBUG - CHATBOT ROUTE")
        print(f"{'='*80}")
        print(f"📋 Session Data:")
        print(f"   user_id: {user_id}")
        print(f"   roleplay_id: {session.get('roleplay_id')}")
        print(f"   cluster_id from session: {cluster_id}")
        print(f"   All session keys: {list(session.keys())}")
        
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
                
                # First, let's see ALL data in the cluster
                cur.execute("SELECT id, name, type FROM roleplay_cluster WHERE id = %s", (cluster_id,))
                result = cur.fetchone()
                if result:
                    cluster_type = result[2]  # type is the 3rd column (index 2)
                    print(f"\n✅ FOUND cluster in database:")
                    print(f"   Cluster ID: {result[0]}")
                    print(f"   Cluster Name: {result[1]}")
                    print(f"   Cluster Type: '{result[2]}'")
                    print(f"   Type datatype: {type(cluster_type)}")
                    print(f"   Type repr: {repr(cluster_type)}")
                else:
                    print(f"\n❌ WARNING: No cluster found with id {cluster_id} in database!")
                
                # Also check which clusters this roleplay belongs to
                cur.execute("""
                    SELECT rc.id, rc.name, rc.type 
                    FROM roleplay_cluster rc
                    JOIN cluster_roleplay cr ON rc.id = cr.cluster_id
                    WHERE cr.roleplay_id = %s
                """, (session.get('roleplay_id'),))
                all_clusters = cur.fetchall()
                if all_clusters:
                    print(f"\n📊 This roleplay exists in {len(all_clusters)} cluster(s):")
                    for cluster in all_clusters:
                        marker = "👉" if cluster[0] == cluster_id else "   "
                        print(f"   {marker} ID: {cluster[0]}, Name: '{cluster[1]}', Type: '{cluster[2]}'")
                
                cur.close()
                conn.close()
            except Exception as e:
                print(f"\n❌ ERROR fetching cluster type: {e}")
                import traceback
                traceback.print_exc()
        
        # If no cluster_id in session, try to get it from user_cluster table
        elif user_id:
            print(f"\n⚠️  WARNING: No cluster_id in session, falling back to database query")
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
                    SELECT uc.cluster_id, rc.type, rc.name
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
                    print(f"   ⚠️  Found cluster from user_cluster (using LIMIT 1):")
                    print(f"   Cluster ID: {cluster_id}, Type: '{cluster_type}', Name: '{result[2]}'")
                    print(f"   ⚠️  WARNING: If roleplay in multiple clusters, this may be wrong!")
                else:
                    print(f"   ❌ No cluster found for user {user_id} and roleplay {roleplay_id}")
                cur.close()
                conn.close()
            except Exception as e:
                print(f"\n❌ ERROR querying user_cluster: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"\n🎯 FINAL RESULT:")
        print(f"   cluster_type = '{cluster_type}'")
        print(f"   Will be sent to template as context['cluster_type']")
        print(f"{'='*80}\n")
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
        
        # Calculate elapsed time for current interaction timer
        if 'interaction_start_time' in session:
            interaction_elapsed = int(time.time() - session['interaction_start_time'])
            context["interaction_elapsed_time"] = interaction_elapsed
        else:
            context["interaction_elapsed_time"] = 0

        if 'comp_dialogue' in session:
            comp_dialogue = session["comp_dialogue"]
            # Translate AI dialogue if not in English
            if selected_language != 'English':
                comp_dialogue = translate_text(comp_dialogue, selected_language)
            context["comp_dialogue"] = comp_dialogue
            context["last_round_result"] = session["last_round_result"]
            context["score"] = session["score"]
            context["image"] = reader_obj.get_images(session['image_interaction_number'])["images"][context["score"]-1]
            print(f"🖼️ DEBUG IMAGE: Interaction image URL = {context['image']}")

        context["data"] = reader_obj.get_interaction(session['interaction_number'])
        
        print(f"DEBUG COMPLETION CHECK: interaction_number={session['interaction_number']}, context['data']={context['data']}")
        
        # Extract character and determine gender for voice
        if context["data"]:
            # Helper function to detect gender from speaker text
            def detect_gender(speaker_text):
                """
                Detect gender from speaker name/text using markers in the cell:
                Formats supported:
                - "Bheem (M): Hello" → Male
                - "Kalyani (F): Hello" → Female
                - "Mr. Smith: Hello" → Male (title detection)
                - "Ms. Jones: Hello" → Female (title detection)
                Default: Male
                """
                if not speaker_text:
                    return "male"  # default
                
                text = str(speaker_text).strip()
                text_lower = text.lower()
                
                # Method 1: Explicit gender markers (M), (F), (Male), (Female)
                if '(m)' in text_lower or '(male)' in text_lower:
                    print(f"✓ Gender from marker: {text[:30]}... = male")
                    return "male"
                
                if '(f)' in text_lower or '(female)' in text_lower:
                    print(f"✓ Gender from marker: {text[:30]}... = female")
                    return "female"
                
                # Method 2: Title/prefix detection in speaker name
                male_titles = ['mr.', 'mr', 'sir', 'mister', 'lord', 'king', 'prince']
                female_titles = ['ms.', 'mrs.', 'miss', 'madam', 'lady', 'queen', 'princess']
                
                for title in male_titles:
                    if text_lower.startswith(title) or f' {title} ' in text_lower:
                        print(f"✓ Gender from title: {text[:30]}... = male (found '{title}')")
                        return "male"
                
                for title in female_titles:
                    if text_lower.startswith(title) or f' {title} ' in text_lower:
                        print(f"✓ Gender from title: {text[:30]}... = female (found '{title}')")
                        return "female"
                
                # Method 3: Default fallback
                print(f"⚠ Gender unknown for '{text[:30]}...', using default: male")
                return "male"
            
            # IMPORTANT: Player is always SINGLE person
            # Column B is for COMPUTER RESPONSE characters (who speaks back to player)
            # Computer response can have TEAM of people responding
            
            character = context["data"].get("character")
            characters = context["data"].get("characters", [])
            
            # Get the computer dialogue that will be read out
            dialogue = session.get("comp_dialogue", "")
            
            # Parse dialogue into speaker segments for multi-voice team roleplays
            # Format: "Bheem: Hello Sir | Satyam: Good morning"
            dialogue_segments = []
            speakers = []
            primary_speaker = None
            
            if dialogue:
                # Split dialogue into lines (handle both \n and | separators)
                lines = dialogue.replace('\n', '|').split('|')
                print(f"DEBUG DIALOGUE PARSING: Total lines after split: {len(lines)}")
                print(f"DEBUG DIALOGUE PARSING: Raw dialogue text:\n{dialogue}")
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    print(f"DEBUG DIALOGUE PARSING: Processing line: '{line}'")
                    
                    # Check if line has "Name: dialogue" format
                    if ':' in line:
                        parts = line.split(':', 1)  # Split only on first colon
                        speaker_name_raw = parts[0].strip()
                        speaker_text = parts[1].strip() if len(parts) > 1 else ""
                        
                        # Validate it's a name (not "Others nod", URLs, etc.)
                        skip_words = ['http', 'https', 'others nod', 'everyone nods', 'all nod', 'scenario']
                        validation_passed = (speaker_name_raw and len(speaker_name_raw) < 50 and not speaker_name_raw.isdigit() 
                            and not any(skip in speaker_name_raw.lower() for skip in skip_words)
                            and speaker_text)  # Must have actual dialogue
                        
                        if not validation_passed:
                            print(f"❌ SKIPPED LINE: Speaker='{speaker_name_raw}' - Failed validation (text='{speaker_text[:30] if speaker_text else 'EMPTY'}...')")
                        
                        if validation_passed:
                            
                            # Detect gender from speaker name (may contain markers like "(M)" or "(F)")
                            speaker_gender = detect_gender(speaker_name_raw)
                            
                            # Clean speaker name: Remove gender markers for display
                            # "Bheem (M)" → "Bheem"
                            speaker_name = speaker_name_raw
                            import re
                            speaker_name = re.sub(r'\s*\([MFmf]\)|\s*\((male|female|Male|Female)\)', '', speaker_name).strip()
                            
                            # Add segment
                            dialogue_segments.append({
                                'speaker': speaker_name,
                                'text': speaker_text,
                                'gender': speaker_gender
                            })
                            print(f"✅ ADDED SEGMENT: Speaker='{speaker_name}' ({speaker_gender}) - Text='{speaker_text[:50]}...'")
                            
                            if speaker_name not in speakers:
                                speakers.append(speaker_name)
                            
                            if not primary_speaker:
                                primary_speaker = speaker_name
                    else:
                        # Line without "Name:" format - add as generic text
                        if line.lower() not in ['others nod', 'everyone nods', 'all nod']:
                            # Add as a segment with no specific speaker
                            dialogue_segments.append({
                                'speaker': '',
                                'text': line,
                                'gender': 'female'  # default
                            })
                
                if dialogue_segments:
                    print(f"DEBUG VOICE: Parsed {len(dialogue_segments)} dialogue segments from {len(speakers)} speakers")
                    for i, seg in enumerate(dialogue_segments):
                        print(f"  Segment {i+1}: {seg['speaker']} ({seg['gender']}) - '{seg['text'][:50]}...'")
            
            # Fallback: Use character names from Excel column B if no segments parsed
            if not dialogue_segments and characters and len(characters) > 0:
                primary_speaker = characters[0]
                speakers = characters
                print(f"DEBUG VOICE: No dialogue segments parsed, using Excel Column B characters: {characters}")
            
            # Check for gender marker from Excel Column B (single-speaker roleplays)
            gender_marker = context["data"].get("gender_marker")
            
            # Translate dialogue segments text if not in English
            if dialogue_segments and selected_language != 'English':
                for segment in dialogue_segments:
                    if segment.get('text'):
                        segment['text'] = translate_text(segment['text'], selected_language)
                print(f"DEBUG VOICE: Translated {len(dialogue_segments)} dialogue segments to {selected_language}")
            
            # Set dialogue segments for multi-voice audio playback
            context["dialogue_segments"] = dialogue_segments
            context["has_multiple_speakers"] = len(dialogue_segments) > 1
            
            # Determine character and gender for audio (for computer response voice)
            if dialogue_segments:
                # Multi-speaker roleplay: Use first segment's speaker as primary
                first_segment = dialogue_segments[0]
                context["character"] = first_segment['speaker']
                context["gender"] = first_segment['gender']
                context["all_speakers"] = speakers
                context["is_team_roleplay"] = len(speakers) > 1
                print(f"DEBUG VOICE: Multi-speaker roleplay - {len(dialogue_segments)} segments, {len(speakers)} unique speakers")
            elif gender_marker:
                # Single-speaker roleplay: Use gender marker from Column B "other (M)" or "other (F)"
                context["character"] = ""
                context["gender"] = gender_marker
                context["is_team_roleplay"] = False
                context["dialogue_segments"] = []  # Empty for single voice
                print(f"DEBUG VOICE: Single-speaker roleplay - Gender from Column B marker: {gender_marker}")
            elif primary_speaker:
                # Team roleplay with multiple people in computer response
                context["character"] = primary_speaker
                context["gender"] = detect_gender(primary_speaker)
                context["all_speakers"] = speakers
                context["is_team_roleplay"] = len(speakers) > 1
                context["dialogue_segments"] = []  # Empty for single voice
                print(f"DEBUG VOICE: Computer response - Primary speaker='{primary_speaker}', Gender={context['gender']}, Team={len(speakers) > 1}")
            elif character:
                # Single character in computer response (from Excel column B)
                context["character"] = character
                context["gender"] = detect_gender(character)
                context["is_team_roleplay"] = False
                context["dialogue_segments"] = []  # Empty for single voice
                print(f"DEBUG VOICE: Computer response - Single character='{character}', Gender={context['gender']}")
            else:
                # No character specified - use default male voice
                context["character"] = ""
                context["gender"] = "male"  # Default to male voice
                context["is_team_roleplay"] = False
                context["dialogue_segments"] = []  # Empty for single voice
                print(f"DEBUG VOICE: No character/gender detected, using default MALE voice")
        if context["data"] == False:
            print(f"🏁 ROLEPLAY COMPLETE DETECTED! Setting completion overlay flags...")
            
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
                
                # Get roleplay config for attempts and ideal video info
                roleplay_id_for_config = session.get('roleplay_id')
                cur.execute("""
                    SELECT repeat_attempts_allowed, show_ideal_video, ideal_video_path
                    FROM roleplay_config WHERE roleplay_id = %s
                """, (roleplay_id_for_config,))
                config_row = cur.fetchone()
                
                max_attempts = config_row[0] if config_row and config_row[0] else 1
                show_ideal_video = bool(config_row[1]) if config_row else False
                ideal_video_path = config_row[2] if config_row and len(config_row) > 2 else None
                
                print(f"🎬 Ideal video config: show={show_ideal_video}, path={ideal_video_path}")
                
                # Count completed attempts for this user and roleplay
                user_id = session.get('user_id')
                cur.execute("""
                    SELECT COUNT(*) FROM play 
                    WHERE user_id = %s AND roleplay_id = %s AND status = 'completed'
                """, (user_id, roleplay_id_for_config))
                completed_attempts = cur.fetchone()[0]
                
                # Check if user has viewed optimal roleplay
                cur.execute("""
                    SELECT COUNT(*) FROM play 
                    WHERE user_id = %s AND roleplay_id = %s AND viewed_optimal = 1
                """, (user_id, roleplay_id_for_config))
                has_viewed_optimal = cur.fetchone()[0] > 0
                
                cur.close()
                conn.close()
                print(f"Updated play {session['play_id']} status to 'completed'")
                print(f"🔢 Attempts: max={max_attempts}, completed={completed_attempts}, viewed_optimal={has_viewed_optimal}")
            except Exception as e:
                print(f"Error updating play status: {str(e)}")
                max_attempts = 1
                completed_attempts = 1
                has_viewed_optimal = False
                show_ideal_video = False
                ideal_video_path = None
            
            # Set flags for completion overlay to show on chatbot page
            context["is_final_interaction"] = True
            context["is_final"] = True
            
            # Set completion message and home URL for overlay
            user_id = session.get('user_id')
            cluster_id = session.get('cluster_id', 1)
            context["home_url"] = url_for('user_cluster_view', user_id=user_id, cluster_id=cluster_id)
            
            # Attempts and retry logic
            attempts_remaining = max(0, max_attempts - completed_attempts)
            context["max_attempts"] = max_attempts
            context["completed_attempts"] = completed_attempts
            context["attempts_remaining"] = attempts_remaining
            context["has_viewed_optimal"] = has_viewed_optimal
            
            # Retry is allowed if: more than 1 attempt allowed AND attempts remaining AND not viewed optimal
            context["can_retry"] = (max_attempts > 1) and (attempts_remaining > 0) and (not has_viewed_optimal)
            context["retry_disabled"] = not context["can_retry"]
            
            # Ideal video logic
            context["show_ideal_video"] = show_ideal_video and ideal_video_path
            context["ideal_video_path"] = ideal_video_path
            # Show warning about losing retry if multiple attempts allowed AND attempts remaining
            context["show_optimal_warning"] = (max_attempts > 1) and (attempts_remaining > 0) and (not has_viewed_optimal)
            
            # Check cluster type for assessment vs training
            # NOTE: cluster_type is already fetched earlier in chatbot route and stored in context["cluster_type"]
            # Use that value instead of trying to get from session (which doesn't store it)
            cluster_type = context.get("cluster_type", "training")
            print(f"🎯 FINAL INTERACTION: cluster_type from context = '{cluster_type}'")
            
            if cluster_type == 'assessment':
                context["can_retry"] = False
                context["retry_disabled"] = True
                context["completion_message"] = "Great work! You completed this assessment."
            else:
                context["completion_message"] = "Great work! You completed this training roleplay."
            
            print(f"Showing completion overlay: cluster_type={cluster_type}, can_retry={context['can_retry']}, show_optimal={context['show_ideal_video']}, warning={context['show_optimal_warning']}")
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
        
        # Pass 16PF configuration to template for audio recording
        pf16_config = get_16pf_config_for_roleplay(roleplay_id)
        context["enable_16pf_analysis"] = pf16_config.get('enable_16pf_analysis', False) if pf16_config else False
        print(f"DEBUG 16PF: enable_16pf_analysis={context['enable_16pf_analysis']}")
        
        # Ensure interaction_elapsed_time is set (in case it wasn't set above)
        if "interaction_elapsed_time" not in context:
            context["interaction_elapsed_time"] = 0
        
        print(f"DEBUG AUDIO: input_type={context['input_type']}, voice_enabled={context['voice_enabled']}")
        print(f"DEBUG TIMER: interaction_elapsed={context.get('interaction_elapsed_time', 0)}, total_elapsed={context.get('elapsed_time', 0)}")

        # PRE-GENERATE AUDIO: Create audio file before rendering template so it's cached when page loads
        # This eliminates the delay when loading the audio player
        try:
            audio_text = context.get('comp_dialogue') or context.get('scenario', '')
            if audio_text:
                from gtts import gTTS
                import hashlib
                
                # Get language code
                language_map = {
                    'English': 'en', 'Hindi': 'hi', 'Tamil': 'ta', 'Telugu': 'te',
                    'Kannada': 'kn', 'Marathi': 'mr', 'Bengali': 'bn', 'Malayalam': 'ml',
                    'French': 'fr', 'Arabic': 'ar', 'Gujarati': 'gu'
                }
                lang_code = language_map.get(selected_language, 'en')
                
                # Create cache directory
                cache_dir = os.path.join(app.root_path, 'static', 'audio_cache')
                os.makedirs(cache_dir, exist_ok=True)
                
                # Generate filename (same logic as make_audio route)
                text_hash = abs(hash(audio_text)) % (10 ** 10)
                filename = f'speech_{text_hash}_{lang_code}.mp3'
                filepath = os.path.join(cache_dir, filename)
                
                # Generate audio if not cached
                if not os.path.exists(filepath):
                    tts = gTTS(text=audio_text, lang=lang_code, slow=False)
                    tts.save(filepath)
                    print(f"✅ Pre-generated audio: {filename}")
                else:
                    print(f"✅ Audio already cached: {filename}")
        except Exception as e:
            print(f"⚠️ Audio pre-generation failed (will generate on demand): {e}")

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
        
        # Validate password against policy
        is_valid, error_message = validate_password(password)
        if not is_valid:
            flash(error_message)
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
            # Set session for admin - make it permanent to avoid auto-logout
            session.permanent = True  # Session will last for PERMANENT_SESSION_LIFETIME (7 days)
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
        
        # Extract filenames from full paths for display
        if roleplay:
            roleplay_with_filenames = list(roleplay)
            # Roleplay tuple schema: id(0), name(1), file_path(2), image_file_path(3), competency_file_path(4), 
            # scenario(5), person_name(6), created_at(7), updated_at(8), scenario_file_path(9), logo_path(10)
            
            print(f"DEBUG RAW DATA: id={roleplay_with_filenames[0]}, name={roleplay_with_filenames[1]}")
            print(f"DEBUG RAW DATA: file_path(2)='{roleplay_with_filenames[2]}' (type: {type(roleplay_with_filenames[2]).__name__})")
            print(f"DEBUG RAW DATA: image_file_path(3)='{roleplay_with_filenames[3]}' (type: {type(roleplay_with_filenames[3]).__name__})")
            print(f"DEBUG RAW DATA: competency_file_path(4)='{roleplay_with_filenames[4]}' (type: {type(roleplay_with_filenames[4]).__name__})")
            print(f"DEBUG RAW DATA: scenario_file_path(9)='{roleplay_with_filenames[9]}' (type: {type(roleplay_with_filenames[9]).__name__})")
            print(f"DEBUG RAW DATA: logo_path(10)='{roleplay_with_filenames[10]}' (type: {type(roleplay_with_filenames[10]).__name__})")
            
            # Helper function to safely extract filename from path (handles datetime objects)
            def safe_basename(path):
                """Safely extract filename, handling None, datetime, and string types"""
                if path is None:
                    return None
                # If it's a datetime object, it's corrupted data - return None
                if isinstance(path, datetime.datetime):
                    print(f"WARNING: Found datetime object in file path: {path}")
                    return None
                # Only process if it's a string and not empty
                if isinstance(path, str) and path.strip():
                    try:
                        return os.path.basename(path)
                    except Exception as e:
                        print(f"ERROR extracting basename from '{path}': {e}")
                        return None
                return None
            
            # Extract filenames and append to indices 11-15
            # file_path (index 2) -> append to index 11
            roleplay_with_filenames.append(safe_basename(roleplay_with_filenames[2]))
            
            # image_file_path (index 3) -> append to index 12
            roleplay_with_filenames.append(safe_basename(roleplay_with_filenames[3]))
            
            # competency_file_path (index 4) -> append to index 13
            roleplay_with_filenames.append(safe_basename(roleplay_with_filenames[4]))
            
            # scenario_file_path (index 9) -> append to index 14
            roleplay_with_filenames.append(safe_basename(roleplay_with_filenames[9]))
            
            # logo_path (index 10) -> append to index 15
            roleplay_with_filenames.append(safe_basename(roleplay_with_filenames[10]))
            
            print(f"DEBUG EXTRACTED: RP(11)={roleplay_with_filenames[11]}, Img(12)={roleplay_with_filenames[12]}, Comp(13)={roleplay_with_filenames[13]}, Scenario(14)={roleplay_with_filenames[14]}, Logo(15)={roleplay_with_filenames[15]}")
            
            return render_template('adminview.html', roleplay=tuple(roleplay_with_filenames), config=config)
        
        return render_template('adminview.html', roleplay=roleplay, config=config)
    return render_template('adminview.html', roleplay=None, config=None)

@app.route("/admin/delete/<path:id>", methods=['GET'])
@admin_required
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
        original_filename = files['roleplay_logo'].filename
        # Check file extension BEFORE modifying filename
        file_ext = os.path.splitext(original_filename)[1].lower()
        if file_ext not in [ext.lower() for ext in app.config['UPLOAD_EXTENSIONS_IMAGES']]:
            flash("Invalid logo file extension. Please use an image file (jpg, jpeg, png, gif, bmp, webp).")
            return redirect(request.referrer or url_for('adminview'))
        
        logo_file = f"{file_id}_{int(time.time())}_logo_{original_filename}"
        logo_file = logo_file.replace('/', '_').replace('\\', '_')
        logo_path = os.path.join(app.config['UPLOAD_PATH_IMAGES'], logo_file)
        
        os.makedirs(os.path.dirname(logo_path), exist_ok=True)
        
        try:
            files['roleplay_logo'].save(logo_path)
            
            # Also copy to static/images so it can be served by Flask
            import shutil
            static_logo_path = os.path.join('app', 'static', 'images', logo_file)
            os.makedirs(os.path.dirname(static_logo_path), exist_ok=True)
            shutil.copy2(logo_path, static_logo_path)
            
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
            return redirect(request.referrer or url_for('adminview'))
    
    # Handle competency file upload - save per roleplay, not globally
    competency_file_path = ''
    if files.get("comp_file"):
        # Use ID for unique competency file naming
        file_id = id if id else f"temp_{int(time.time())}"
        comp_filename = f"{file_id}_competency.xlsx"
        comp_filename = comp_filename.replace('/', '_').replace('\\', '_')
        competency_file_path = os.path.join(app.config['UPLOAD_PATH_COMP'], comp_filename)
        
        file_ext = os.path.splitext(files['comp_file'].filename)[1].lower()
        if file_ext not in [ext.lower() for ext in app.config['UPLOAD_EXTENSIONS_COMP']]:
            flash("Invalid competency file extension.")
            return redirect(request.referrer or url_for('adminview'))
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(competency_file_path), exist_ok=True)
        
        try:
            files['comp_file'].save(competency_file_path)
            print(f"Saved competency file to: {competency_file_path}")
        except PermissionError:
            flash("⚠️ Cannot save competency file - the file is currently open in another program. Please close it and try again.")
            return redirect(request.referrer or url_for('adminview'))
        except Exception as e:
            flash(f"Error saving competency file: {str(e)}")
            return redirect(request.referrer or url_for('adminview'))
    
    # Validate competencies match between roleplay and competency files
    if roleplay_file_path and competency_file_path:
        try:
            print(f"🔍 Validating competency match between roleplay and master file...")
            from reader.excel import ExcelReader
            from reader.master import MasterReader
            
            # Load both files
            test_reader = ExcelReader(roleplay_file_path, None, competency_file_path)
            
            # Try to load first interaction to trigger competency validation
            try:
                test_reader.get_interaction(1)
                print(f"✅ Competency validation passed!")
            except ValueError as comp_error:
                error_msg = str(comp_error)
                if "Could not find competency" in error_msg:
                    # Extract competency name and available list from error
                    flash(f"❌ Competency Mismatch Error: {error_msg}")
                    flash("⚠️ Please check that all competencies in the roleplay Excel match the competency master file exactly (including spelling, spacing, and case).")
                    
                    # Clean up uploaded files
                    if os.path.exists(roleplay_file_path):
                        os.remove(roleplay_file_path)
                    if os.path.exists(competency_file_path):
                        os.remove(competency_file_path)
                    
                    return redirect(request.referrer or url_for('adminview'))
                else:
                    # Re-raise if different error
                    raise
                    
        except Exception as e:
            print(f"⚠️ Competency validation warning: {str(e)}")
            # Don't block upload for other errors, just log them

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
    new_id = create_or_update(id, name, person_name, scenario, roleplay_file_path, image_file_path, competency_file_path, scenario_file_path, logo_path)
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
            'difficulty_level': form.get('difficulty_level', 'easy'),
            # 16PF Voice Analysis Configuration
            'enable_16pf_analysis': form.get('enable_16pf_analysis') == 'on',
            'pf16_analysis_source': form.get('pf16_analysis_source', 'none'),
            'pf16_user_age_required': form.get('pf16_user_age_required') == 'on',
            'pf16_user_gender_required': form.get('pf16_user_gender_required') == 'on',
            'pf16_default_age': int(form.get('pf16_default_age', 30)),
            'pf16_send_audio_for_analysis': form.get('pf16_send_audio_for_analysis') == 'on'
        }
        
        create_or_update_roleplay_config(new_id, config_data)
        
    except Exception as e:
        print(f"Error saving roleplay config: {str(e)}")
        flash("Roleplay saved but configuration failed to save")
    
    # Show appropriate message based on whether it was an update or creation
    if id:
        flash(f'Roleplay has been successfully updated!')
    else:
        flash(f'Roleplay has been successfully added!')
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


@app.route("/mark_optimal_viewed/<int:play_id>", methods=['POST'])
def mark_optimal_viewed(play_id):
    """Mark that the user has viewed the optimal roleplay video"""
    try:
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME', 'roleplay')
        )
        cur = conn.cursor()
        cur.execute("""
            UPDATE play SET viewed_optimal = 1 WHERE id = %s
        """, (play_id,))
        conn.commit()
        cur.close()
        conn.close()
        print(f"✅ Marked play {play_id} as viewed_optimal=1")
        return jsonify({"success": True})
    except Exception as e:
        print(f"❌ Error marking optimal viewed: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/process_response", methods=['GET', 'POST'])
def process_response():
    """Process the user response and return JSON for AJAX calls"""
    # Handle POST request from AJAX form submission
    if request.method == 'POST':
        from app.forms import PostForm
        form = PostForm()
        if form.validate_on_submit():
            session['user_input'] = form.post.data.strip()
    
    # Check if user_input is in session
    if 'user_input' not in session:
        if request.method == 'POST':
            return jsonify({"success": False, "message": "No user input provided"}), 400
        return redirect(url_for('index'))
    
    # Process the AI response
    success, redirect_url, message = _process_ai_and_update_session()
    
    # Return JSON for AJAX requests
    if request.method == 'POST':
        if not success:
            return jsonify({"success": False, "message": message}), 500
        return jsonify({"success": True, "redirect_url": redirect_url})
    
    # Handle GET requests (legacy support)
    if not success:
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
        # Check if this is a timeout auto-submit
        user_input = session.get('user_input', '')
        is_timeout = user_input == '[TIMEOUT_NO_RESPONSE]'
        
        if is_timeout:
            # User didn't respond in time - give 0 score
            print("DEBUG: Timeout detected - user did not respond in time")
            
            # Replace marker with a neutral message for display
            session['user_input'] = 'No response provided (time expired)'
            
            # Get reader for interaction data
            roleplay_competencies = get_roleplay_competencies()
            reader_obj = reader.excel.ExcelReader(session["exr_param0"], roleplay_competencies, session["exr_param2"])
            
            # Get interaction data to know what the next interaction should be
            interaction_data = reader_obj.get_interaction(session["interaction_number"])
            
            # Create chat entry with 0 score
            chathistory_id = create_chat_entry(session['user_input'], "Please provide a response next time.")
            scoremaster_id = create_score_master(chathistory_id, 0)
            
            # Get all competencies and set them to 0
            name_change_dict = {
                "Sentiment": "Sentiment/Keyword Match Score",
                "Instruction Following": "Aligned to best practice score"
            }
            session["last_round_result"] = {}
            
            # Set all competency scores to 0
            for competency in interaction_data.get("competencies", []):
                comp_name = competency.get("name", "Unknown")
                create_score_breakdown(scoremaster_id, comp_name, 0)
                session["last_round_result"][comp_name] = 0
            
            # Add sentiment and instruction following with 0 score
            create_score_breakdown(scoremaster_id, "Sentiment/Keyword Match Score", 0)
            create_score_breakdown(scoremaster_id, "Aligned to best practice score", 0)
            session["last_round_result"]["Sentiment/Keyword Match Score"] = 0
            session["last_round_result"]["Aligned to best practice score"] = 0
            
            session["score"] = 0
            session["comp_dialogue"] = "Please provide a response next time."
            session["image_interaction_number"] = session["interaction_number"]
            
            # Move to next interaction (using score of 1 for flow, but recorded score is 0)
            next_interaction = reader_obj.get_next_interaction(session["interaction_number"], 1)
            session["interaction_number"] = next_interaction
            
        else:
            # Normal processing with AI
            roleplay_competencies = get_roleplay_competencies()
            reader_obj = reader.excel.ExcelReader(session["exr_param0"], roleplay_competencies, session["exr_param2"])
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
        
        # Set new interaction start time for the next interaction
        import time
        session["interaction_start_time"] = time.time()

        # Clean up
        session.pop('user_input', None)

        # Check if conversation has ended (interaction_number = -1)
        if session["interaction_number"] == -1:
            # Mark play as completed
            from app.queries import mark_play_completed
            if 'play_id' in session:
                mark_play_completed(session['play_id'])
            
            # Redirect back to chatbot page to show completion overlay
            redirect_url = url_for('chatbot', roleplay_id=session['roleplay_id'], interaction_num=session['interaction_number'])
        else:
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
    
    # Get user's attempted roleplays with status
    conn = mysql.connector.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME', 'roleplay')
    )
    cur = conn.cursor(dictionary=True)
    
    cur.execute("""
        SELECT p.id, p.roleplay_id, p.cluster_id, p.status, p.start_time, p.end_time,
               r.name as roleplay_name, r.person_name, rc.name as cluster_name,
               ROUND(AVG(sm.overall_score)) as score_total
        FROM play p
        JOIN roleplay r ON p.roleplay_id = r.id
        JOIN roleplay_cluster rc ON p.cluster_id = rc.id
        LEFT JOIN chathistory ch ON ch.play_id = p.id
        LEFT JOIN scoremaster sm ON sm.chathistory_id = ch.id
        WHERE p.user_id = %s AND p.status IN ('completed', 'optimal_viewed')
        GROUP BY p.id, p.roleplay_id, p.cluster_id, p.status, p.start_time, p.end_time,
                 r.name, r.person_name, rc.name
        ORDER BY p.start_time DESC
    """, (user_id,))
    
    attempted_roleplays = cur.fetchall()
    cur.close()
    conn.close()
    
    return render_template('admin_user_detail.html', 
                         user=user, 
                         all_clusters=all_clusters,
                         user_clusters=user_clusters,
                         assigned_cluster_ids=assigned_cluster_ids,
                         attempted_roleplays=attempted_roleplays)

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

@app.route('/admin/users/new', methods=['GET', 'POST'])
@admin_required
def admin_create_user():
    """Create a new user account (admin function)"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        
        if not email or not password or not name:
            flash('All fields are required')
            return render_template('admin_user_form.html')
        
        # Validate password against policy
        is_valid, error_message = validate_password(password)
        if not is_valid:
            flash(error_message)
            return render_template('admin_user_form.html')
        
        # Create user
        user_id, message = create_user_account(email, password)
        
        if user_id:
            flash('User created successfully!')
            return redirect(url_for('admin_users'))
        else:
            flash(f'Failed to create user: {message}')
            return render_template('admin_user_form.html')
    
    return render_template('admin_user_form.html')

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
        # Check if coming from roleplay completion
        if request.args.get('completed'):
            flash('✅ Roleplay completed successfully!', 'success')
        
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
            
            # DEBUG: Print attempt calculation details
            print(f"DEBUG HOMEPAGE - ROLEPLAY {rp[0]} ({rp[1]}): max_attempts={max_attempts}, completed={completed_attempts}, viewed_optimal={viewed_optimal}, in_progress={has_in_progress}")
            
            # If viewed optimal, no attempts remaining
            if viewed_optimal:
                attempts_remaining = 0
                can_reattempt = False
            else:
                # Simple calculation: remaining = max - completed
                # If there's an in-progress attempt, it will soon be completed or abandoned
                # Don't count it toward attempts used until it's actually completed
                attempts_remaining = max(0, max_attempts - completed_attempts)
                can_reattempt = attempts_remaining > 0 and completed_attempts > 0
            
            print(f"DEBUG HOMEPAGE - RESULT: attempts_remaining={attempts_remaining}, can_reattempt={can_reattempt}")
            
            # Determine status
            if viewed_optimal:
                status = 'completed'
            elif completed_attempts >= max_attempts:
                # All attempts used - mark as completed
                status = 'completed'
            elif completed_attempts > 0:
                status = 'attempted'
            elif has_in_progress:
                status = 'in_progress'
            else:
                status = 'not_started'
            
            print(f"DEBUG HOMEPAGE - STATUS: {status} (completed_attempts={completed_attempts}, max_attempts={max_attempts})")
            
            roleplay_data.append({
                'id': rp[0],
                'name': rp[1],  # roleplay name
                'person_name': rp[6],  # character name (FIXED: was rp[5])
                'title': rp[6],  # Use person_name as title (FIXED: was rp[5])
                'scenario': rp[5],  # scenario text (FIXED: was rp[4] which was competency_file_path)
                'scenario_file_path': rp[9] if len(rp) > 9 else None,  # scenario file for download (FIXED: was rp[8])
                'logo_path': rp[10] if len(rp) > 10 else None,  # roleplay logo for tile display (FIXED: was rp[9])
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
                             cluster_id=cluster_id,  # Pass cluster_id explicitly for JavaScript
                             cluster=cluster,
                             roleplays=roleplay_data)
                             
    except Exception as e:
        print(f"Error loading cluster: {str(e)}")
        import traceback
        traceback.print_exc()
        return render_template('500.html'), 500


@app.route('/user/<int:user_id>/cluster/<int:cluster_id>/roleplay/<path:roleplay_id>/complete')
def roleplay_complete(user_id, cluster_id, roleplay_id):
    """Handle roleplay completion - redirect to cluster dashboard"""
    flash('Roleplay completed successfully!')
    return redirect(url_for('user_cluster_view', user_id=user_id, cluster_id=cluster_id))


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
        return redirect(url_for('user_cluster_view', user_id=user_id, cluster_id=cluster_id))
        
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
        
        # Get cluster type to determine behavior
        cluster_type = 'training'  # Default
        try:
            conn = mysql.connector.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                user=os.getenv('DB_USER', 'root'),
                password=os.getenv('DB_PASSWORD'),
                database=os.getenv('DB_NAME', 'roleplay')
            )
            cur = conn.cursor()
            # Get cluster type from roleplay_cluster table
            cur.execute("SELECT type FROM roleplay_cluster WHERE id = %s", (cluster_id,))
            result = cur.fetchone()
            if result:
                cluster_type = result[0]
                print(f"DEBUG COMPLETION: cluster_id={cluster_id}, cluster_type={cluster_type}")
            else:
                print(f"DEBUG COMPLETION: No cluster found with id={cluster_id}, using default 'training'")
                cluster_type = 'training'
            cur.close()
            conn.close()
        except Exception as e:
            print(f"Error fetching cluster type: {e}")
            import traceback
            traceback.print_exc()
        
        # Get roleplay configuration
        roleplay = get_roleplay_with_config(roleplay_id)
        if not roleplay:
            print(f"ERROR: Roleplay not found for id={roleplay_id}")
            flash('Roleplay not found')
            return redirect(url_for('user_cluster_view', user_id=user_id, cluster_id=cluster_id))
        
        print(f"DEBUG COMPLETION: roleplay data length={len(roleplay)}, data={roleplay}")
        
        # Extract configuration values
        # Roleplay table has columns 0-8 (id, name, file_path, image_file_path, competency_file_path, scenario, person_name, created_at, updated_at)
        # Then roleplay_config columns: selected_language(9), video_path(10), input_type(11), audio_rerecord_attempts(12),
        # available_languages(13), max_interaction_time(14), max_total_time(15), repeat_attempts_allowed(16),
        # score_type(17), show_ideal_video(18), ideal_video_path(19), voice_assessment_enabled(20)
        
        # Handle case where roleplay_config might not exist (all columns after index 8 could be None)
        try:
            max_attempts = int(roleplay[16]) if len(roleplay) > 16 and roleplay[16] is not None else 1
        except (ValueError, TypeError, IndexError) as e:
            print(f"DEBUG: Error parsing max_attempts from index 16: {e}, using default 1")
            max_attempts = 1
            
        try:
            show_ideal_video = roleplay[18] if len(roleplay) > 18 and roleplay[18] is not None else False
        except (IndexError, TypeError) as e:
            print(f"DEBUG: Error parsing show_ideal_video from index 18: {e}, using default False")
            show_ideal_video = False
            
        try:
            ideal_video_path = roleplay[19] if len(roleplay) > 19 else None
        except (IndexError, TypeError) as e:
            print(f"DEBUG: Error parsing ideal_video_path from index 19: {e}, using default None")
            ideal_video_path = None
        
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
        
        # Check if there's an in-progress attempt in THIS cluster (shouldn't be any after completion, but check anyway)
        cur.execute("""
            SELECT COUNT(*) FROM play 
            WHERE user_id = %s AND roleplay_id = %s AND cluster_id = %s AND status = 'in_progress'
        """, (user_id, roleplay_id, cluster_id))
        
        has_in_progress = cur.fetchone()[0] > 0
        
        print(f"DEBUG ATTEMPTS: user_id={user_id}, roleplay_id={roleplay_id}, cluster_id={cluster_id}")
        print(f"DEBUG COMPLETION - max_attempts={max_attempts}, completed={completed_attempts}, viewed_optimal={has_viewed_optimal}, in_progress={has_in_progress}")
        
        # If user has viewed optimal video, they cannot retry
        if has_viewed_optimal:
            attempts_remaining = 0
        else:
            # Simple calculation: remaining = max - completed
            # The current attempt should already be marked as 'completed' by the time this page loads
            # so it's already counted in completed_attempts
            attempts_remaining = max(0, max_attempts - completed_attempts)
        
        print(f"DEBUG COMPLETION - attempts_remaining={attempts_remaining}")
        print(f"DEBUG COMPLETION - Rendering template with cluster_type='{cluster_type}'")
        
        # Get score data from the most recent completed play session
        cumul_score = {}
        total_score = 0
        max_score = 0
        
        try:
            # Get the most recent completed play record
            cur.execute("""
                SELECT id FROM play 
                WHERE user_id = %s AND roleplay_id = %s AND cluster_id = %s AND status = 'completed'
                ORDER BY end_time DESC
                LIMIT 1
            """, (user_id, roleplay_id, cluster_id))
            
            latest_play = cur.fetchone()
            
            if latest_play:
                play_id = latest_play[0]
                
                # Get all scores for this play session
                cur.execute("""
                    SELECT competency, score FROM scores 
                    WHERE play_id = %s
                    ORDER BY id
                """, (play_id,))
                
                scores = cur.fetchall()
                print(f"DEBUG SCORES: Found {len(scores)} score records for play_id={play_id}")
                
                # Aggregate scores by competency
                for comp, score in scores:
                    if comp not in cumul_score:
                        cumul_score[comp] = {'score': 0, 'total': 0}
                    cumul_score[comp]['score'] += score
                    cumul_score[comp]['total'] += 3  # Max score per interaction is 3
                    total_score += score
                    max_score += 3
                
                print(f"DEBUG SCORES: total_score={total_score}, max_score={max_score}")
                print(f"DEBUG SCORES: cumul_score={cumul_score}")
            else:
                print(f"DEBUG SCORES: No completed play found for user_id={user_id}, roleplay_id={roleplay_id}, cluster_id={cluster_id}")
                
        except Exception as e:
            print(f"Error fetching scores: {str(e)}")
            import traceback
            traceback.print_exc()
        
        cur.close()
        conn.close()
        
        return render_template('roleplay_completion.html',
                             user_id=user_id,
                             cluster_id=cluster_id,
                             roleplay_id=roleplay_id,
                             max_attempts=max_attempts,
                             attempts_remaining=attempts_remaining,
                             show_ideal_video=show_ideal_video,
                             ideal_video_path=ideal_video_path,
                             cluster_type=cluster_type,
                             cumul_score=cumul_score,
                             total_score=total_score,
                             max_score=max_score)
    
    except Exception as e:
        print(f"Error in roleplay_completion: {str(e)}")
        import traceback
        print("Full traceback:")
        traceback.print_exc()
        flash(f'Error loading completion page: {str(e)}')
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
        
        # Column index 16 is ideal_video_path (not 14)
        ideal_video_path = roleplay[16] if roleplay[16] is not None else None  # ideal_video_path
        
        if not ideal_video_path:
            flash('No optimal roleplay video available')
            return redirect(url_for('user_cluster_view', user_id=user_id, cluster_id=cluster_id))
        
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
        return redirect(url_for('user_cluster_view', user_id=user_id, cluster_id=cluster_id))

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
        
        # Generate PDF report (pass play_id for 16PF data)
        report_path = generate_roleplay_report(
            user_name=user_name,
            user_email=user_email,
            roleplay_name=roleplay_name,
            scenario=scenario,
            overall_score=overall_score,
            score_breakdown=score_breakdown,
            interactions=interactions,
            play_id=play_id  # For fetching 16PF voice analysis data
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


@app.route('/download_report/<int:play_id>', methods=['GET'])
def download_report(play_id):
    """Download performance report PDF for a completed roleplay"""
    try:
        print(f"\n=== DOWNLOAD REPORT DEBUG ===")
        print(f"Play ID: {play_id}")
        
        # Get play information
        play_info = get_play_info(play_id)
        print(f"Play info: {play_info}")
        
        if not play_info:
            print("ERROR: Play session not found")
            flash('Play session not found')
            return redirect(url_for('index'))
        
        user_id = play_info[3]
        roleplay_id = play_info[4]
        print(f"User ID: {user_id}, Roleplay ID: {roleplay_id}")
        
        # Get user information
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME', 'roleplay')
        )
        cur = conn.cursor()
        
        # Get user email
        cur.execute("SELECT email FROM user WHERE id = %s", (user_id,))
        user_data = cur.fetchone()
        if not user_data:
            flash('User not found')
            return redirect(url_for('index'))
        
        user_email = user_data[0]
        user_name = user_email.split('@')[0]  # Use email prefix as name
        
        # Get roleplay name
        cur.execute("SELECT name FROM roleplay WHERE id = %s", (roleplay_id,))
        roleplay_data = cur.fetchone()
        roleplay_name = roleplay_data[0] if roleplay_data else "Roleplay"
        
        # Get roleplay details
        cur.execute("SELECT name, scenario FROM roleplay WHERE id = %s", (roleplay_id,))
        roleplay_data = cur.fetchone()
        if not roleplay_data:
            flash('Roleplay not found')
            cur.close()
            conn.close()
            return redirect(request.referrer or url_for('index'))
        
        roleplay_name = roleplay_data[0]
        scenario = roleplay_data[1]
        
        cur.close()
        conn.close()
        
        # Get report data
        from app.queries import query_showreport
        report = query_showreport(play_id)
        
        if not report or len(report) < 3:
            flash('No report data available for this play session')
            return redirect(request.referrer or url_for('index'))
        
        interactions = report[0]
        score_breakdown_list = report[1]  # This has name, score, total_possible
        overall_score_dict = report[2].get('overall_score', {"score": 0, "total": 0})
        overall_score = float(overall_score_dict.get('score', 0))
        
        print(f"DEBUG: Score breakdown list: {score_breakdown_list}")
        
        # Generate PDF report - pass the raw score breakdown list (with play_id for 16PF data)
        from app.report_generator_v2 import generate_roleplay_report
        report_path = generate_roleplay_report(
            user_name=user_name,
            user_email=user_email,
            roleplay_name=roleplay_name,
            scenario=scenario,
            overall_score=overall_score,
            score_breakdown=score_breakdown_list,  # Pass the list directly
            interactions=interactions,
            play_id=play_id  # For fetching 16PF voice analysis data
        )
        
        if not report_path or not os.path.exists(report_path):
            flash('Error generating report')
            return redirect(request.referrer or url_for('index'))
        
        # Send file for download
        return send_file(
            report_path,
            as_attachment=True,
            download_name=f"roleplay_report_{play_id}_{user_name.replace(' ', '_')}.pdf",
            mimetype='application/pdf'
        )
        
    except Exception as e:
        print(f"Error downloading report: {str(e)}")
        import traceback
        print("Full traceback:")
        traceback.print_exc()
        flash(f'Error downloading report: {str(e)}')
        return redirect(request.referrer or url_for('index'))


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
            
            # Check if report generation failed
            if not report or report is None:
                print(f"ERROR: query_showreport returned None for play_id={play_id}")
                return False
            
            print(f"DEBUG REPORT RAW: report type={type(report)}, length={len(report) if report else 0}")
            print(f"DEBUG REPORT RAW: report[0] (interactions) = {report[0] if len(report) > 0 else 'N/A'}")
            print(f"DEBUG REPORT RAW: report[1] (score_breakdown) = {report[1] if len(report) > 1 else 'N/A'}")
            print(f"DEBUG REPORT RAW: report[2] (final_score) = {report[2] if len(report) > 2 else 'N/A'}")
            
            interactions = report[0]
            score_breakdown_list = report[1]  # List of {"name": X, "score": Y, "total_possible": Z}
            # report[2] is final_score dict with structure: {"overall_score": {"score": X, "total": Y}}
            final_score_data = report[2] if len(report) > 2 else {}
            overall_score_dict = final_score_data.get('overall_score', {"score": 0, "total": 0}) if isinstance(final_score_data, dict) else {"score": 0, "total": 0}
            overall_score = overall_score_dict.get('score', 0) if isinstance(overall_score_dict, dict) else 0
            
            # score_breakdown_list is already in the correct format: list of {"name": X, "score": Y, "total_possible": Z}
            # Just pass it directly to the report generator
            print(f"DEBUG: Report data - interactions={len(interactions)}, overall_score={overall_score}")
            print(f"DEBUG: score_breakdown_list = {score_breakdown_list}")
            print(f"DEBUG: Number of competency breakdowns = {len(score_breakdown_list) if score_breakdown_list else 0}")
            
            # Generate PDF report (pass play_id for 16PF data)
            report_path = generate_roleplay_report(
                user_name=user_name,
                user_email=user_email,
                roleplay_name=roleplay_name,
                scenario=scenario,
                overall_score=overall_score,
                score_breakdown=score_breakdown_list,  # Pass the list directly
                interactions=interactions,
                play_id=play_id  # For fetching 16PF voice analysis data
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


# =============================================
# 16PF Voice Analysis API Endpoints
# =============================================

@app.route("/api/16pf/analyze", methods=["POST"])
@admin_required
def api_16pf_analyze():
    """
    Manually trigger 16PF analysis for a specific audio file.
    
    Request JSON:
    {
        "audio_file_path": "/path/to/audio.mp3",
        "play_id": 123 (optional),
        "age": 30 (optional, default 30),
        "gender": "Male" (optional, default "Male")
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"success": False, "error": "No JSON data provided"}), 400
        
        audio_file_path = data.get('audio_file_path')
        if not audio_file_path:
            return jsonify({"success": False, "error": "audio_file_path is required"}), 400
        
        if not os.path.exists(audio_file_path):
            return jsonify({"success": False, "error": f"File not found: {audio_file_path}"}), 404
        
        age = data.get('age', 30)
        gender = data.get('gender', 'Male')
        
        # Run the analysis
        success, result = analyze_audio_for_16pf(
            file_path=audio_file_path,
            age=age,
            gender=gender
        )
        
        if success:
            return jsonify({
                "success": True,
                "personality_scores": result.get('personality_scores', {}),
                "composite_scores": result.get('composite_scores', {}),
                "overall_role_fit": result.get('overall_role_fit'),
                "analysis_confidence": result.get('analysis_confidence'),
                "raw_response": result.get('raw_response')
            })
        else:
            return jsonify({
                "success": False,
                "error": result.get('error', 'Unknown error')
            }), 500
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/16pf/status/<int:play_id>", methods=["GET"])
def api_16pf_status(play_id):
    """Get the 16PF analysis status and results for a play session."""
    try:
        result = get_16pf_analysis_by_play_id(play_id)
        
        if not result:
            return jsonify({
                "success": False,
                "error": "No 16PF analysis found for this play session"
            }), 404
        
        return jsonify({
            "success": True,
            "status": result.get('status'),
            "personality_scores": result.get('personality_scores', {}),
            "composite_scores": result.get('composite_scores', {}),
            "overall_role_fit": result.get('overall_role_fit'),
            "analysis_confidence": result.get('analysis_confidence'),
            "error_message": result.get('error_message'),
            "created_at": str(result.get('created_at')) if result.get('created_at') else None,
            "completed_at": str(result.get('completed_at')) if result.get('completed_at') else None
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/16pf/trigger/<int:play_id>", methods=["POST"])
@admin_required
def api_16pf_trigger(play_id):
    """Manually trigger 16PF analysis for a completed play session."""
    try:
        # Get play info
        play_info = get_play_info(play_id)
        if not play_info:
            return jsonify({"success": False, "error": "Play session not found"}), 404
        
        user_id = play_info[2]
        roleplay_id = play_info[3]
        
        # Get request data for age/gender overrides
        data = request.get_json() or {}
        
        # Find audio file
        audio_file_path = get_audio_file_for_play(play_id)
        if not audio_file_path:
            return jsonify({
                "success": False,
                "error": "No audio file found for this play session"
            }), 404
        
        # Get config or use defaults
        pf16_config = get_16pf_config_for_roleplay(roleplay_id) or {}
        user_age = data.get('age', pf16_config.get('pf16_default_age', 30))
        user_gender = data.get('gender', 'Male')
        analysis_source = data.get('source', pf16_config.get('pf16_analysis_source', 'persona360'))
        
        # Create analysis record
        analysis_id = save_16pf_analysis_result(
            play_id=play_id,
            user_id=user_id,
            roleplay_id=roleplay_id,
            audio_file_path=audio_file_path,
            user_age=user_age,
            user_gender=user_gender,
            analysis_source=analysis_source
        )
        
        if not analysis_id:
            return jsonify({"success": False, "error": "Failed to create analysis record"}), 500
        
        # Run analysis in background
        thread = threading.Thread(
            target=run_16pf_analysis_async,
            args=(analysis_id, audio_file_path, user_age, user_gender, analysis_source)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "success": True,
            "message": "16PF analysis triggered",
            "analysis_id": analysis_id,
            "play_id": play_id,
            "audio_file": audio_file_path
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/16pf/upload-analyze", methods=["POST"])
@admin_required
def api_16pf_upload_analyze():
    """
    Upload an audio/video file and analyze it for 16PF scores.
    
    Form data:
    - file: The audio/video file
    - age: User age (optional, default 30)
    - gender: Male or Female (optional, default Male)
    """
    try:
        if 'file' not in request.files:
            return jsonify({"success": False, "error": "No file uploaded"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"success": False, "error": "No file selected"}), 400
        
        # Get form data
        age = int(request.form.get('age', 30))
        gender = request.form.get('gender', 'Male')
        
        # Save the uploaded file temporarily
        temp_dir = os.path.join(app.root_path, 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        
        filename = f"16pf_upload_{uuid.uuid4().hex[:8]}_{file.filename}"
        temp_path = os.path.join(temp_dir, filename)
        file.save(temp_path)
        
        try:
            # Run the analysis
            success, result = analyze_audio_for_16pf(
                file_path=temp_path,
                age=age,
                gender=gender
            )
            
            if success:
                return jsonify({
                    "success": True,
                    "personality_scores": result.get('personality_scores', {}),
                    "composite_scores": result.get('composite_scores', {}),
                    "overall_role_fit": result.get('overall_role_fit'),
                    "analysis_confidence": result.get('analysis_confidence')
                })
            else:
                return jsonify({
                    "success": False,
                    "error": result.get('error', 'Unknown error')
                }), 500
                
        finally:
            # Clean up temp file
            try:
                os.remove(temp_path)
            except:
                pass
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/16pf/download-audio/<int:play_id>", methods=["GET"])
@admin_required
def download_16pf_audio(play_id):
    """
    Download the audio file used for 16PF analysis for a specific play session.
    
    This is helpful for testing and verifying what audio was sent for analysis.
    """
    try:
        # Get the audio file path from pf16_analysis_results table
        from app.queries import get_16pf_analysis_by_play_id
        
        result = get_16pf_analysis_by_play_id(play_id)
        
        if not result:
            # Try to find it manually
            audio_file_path = get_audio_file_for_play(play_id)
            if not audio_file_path:
                return jsonify({
                    "success": False,
                    "error": f"No audio file found for play_id {play_id}"
                }), 404
        else:
            audio_file_path = result.get('audio_file_path')
            if not audio_file_path:
                return jsonify({
                    "success": False,
                    "error": "Audio file path not recorded in database"
                }), 404
        
        # Check if file exists
        if not os.path.exists(audio_file_path):
            return jsonify({
                "success": False,
                "error": f"Audio file not found at path: {audio_file_path}"
            }), 404
        
        # Get just the filename for download
        filename = os.path.basename(audio_file_path)
        
        return send_file(
            audio_file_path,
            as_attachment=True,
            download_name=f"play_{play_id}_{filename}"
        )
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
