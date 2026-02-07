"""
Security utilities for Rolevo Flask application.
This module contains helper functions for input validation, ownership verification,
and other security-related operations.
"""

import os
import mysql.connector
import time as time_module

# =============================================================================
# SECURITY CONSTANTS
# =============================================================================
MAX_USER_INPUT_LENGTH = 10000  # 10KB max user input
MAX_AUDIO_FILE_SIZE = 50 * 1024 * 1024  # 50MB max audio file
ALLOWED_AUDIO_EXTENSIONS = {'webm', 'wav', 'mp3', 'ogg', 'm4a', 'mp4', 'mpeg', 'mpga'}
TIME_GRACE_PERIOD_SECONDS = 10  # Grace period for time validation


def validate_user_input_length(user_input: str) -> tuple:
    """
    Validate that user input doesn't exceed maximum length.
    
    Args:
        user_input: The user's input string
        
    Returns:
        (is_valid, error_message) tuple
    """
    if not user_input:
        return False, "Input cannot be empty"
    if len(user_input) > MAX_USER_INPUT_LENGTH:
        return False, f"Input too long. Maximum {MAX_USER_INPUT_LENGTH} characters allowed."
    return True, None


def verify_play_ownership(play_id, user_id) -> bool:
    """
    Verify that a play_id belongs to the specified user_id.
    
    This prevents session manipulation attacks where an attacker could
    modify their session to use another user's play_id.
    
    Args:
        play_id: The play session ID
        user_id: The user ID to verify ownership against
        
    Returns:
        True if the play belongs to the user, False otherwise
    """
    if not play_id or not user_id:
        return False
    
    try:
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME', 'roleplay')
        )
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM play WHERE id = %s", (play_id,))
        result = cur.fetchone()
        cur.close()
        conn.close()
        
        if result and result[0] == user_id:
            return True
        return False
    except Exception as e:
        print(f"Error verifying play ownership: {e}")
        return False


def verify_cluster_membership(user_id, cluster_id) -> bool:
    """
    Verify that a user is assigned to a specific cluster.
    
    This prevents users from accessing clusters they're not assigned to.
    
    Args:
        user_id: The user ID
        cluster_id: The cluster ID to check membership for
        
    Returns:
        True if the user is assigned to the cluster, False otherwise
    """
    if not user_id or not cluster_id:
        return False
    
    try:
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME', 'roleplay')
        )
        cur = conn.cursor()
        cur.execute("""
            SELECT 1 FROM user_cluster 
            WHERE user_id = %s AND cluster_id = %s
        """, (user_id, cluster_id))
        result = cur.fetchone()
        cur.close()
        conn.close()
        
        return result is not None
    except Exception as e:
        print(f"Error verifying cluster membership: {e}")
        return False


def validate_audio_file(file_obj) -> tuple:
    """
    Validate audio file type by extension and size.
    
    This prevents uploading of malicious files disguised as audio.
    
    Args:
        file_obj: The uploaded file object
        
    Returns:
        (is_valid, error_message) tuple
    """
    if not file_obj or not file_obj.filename:
        return False, "No file provided"
    
    # Check extension
    ext = file_obj.filename.rsplit('.', 1)[-1].lower() if '.' in file_obj.filename else ''
    if ext not in ALLOWED_AUDIO_EXTENSIONS:
        return False, f"Invalid file type. Allowed: {', '.join(ALLOWED_AUDIO_EXTENSIONS)}"
    
    # Check file size (read position and reset)
    file_obj.seek(0, 2)  # Seek to end
    file_size = file_obj.tell()
    file_obj.seek(0)  # Reset to beginning
    
    if file_size > MAX_AUDIO_FILE_SIZE:
        return False, f"File too large. Maximum {MAX_AUDIO_FILE_SIZE // (1024*1024)}MB allowed."
    
    if file_size == 0:
        return False, "File is empty"
    
    return True, None


def validate_roleplay_time(session_data: dict) -> tuple:
    """
    Validate that the roleplay session hasn't exceeded time limits.
    Server-side validation to prevent client-side timer manipulation.
    
    Args:
        session_data: Dictionary containing session data with timing info
        
    Returns:
        (is_valid, error_message) tuple
    """
    # Check total roleplay time
    if 'roleplay_start_time' in session_data and 'max_total_time' in session_data:
        max_total = session_data.get('max_total_time', 0)
        if max_total > 0:  # 0 means unlimited
            elapsed = time_module.time() - session_data['roleplay_start_time']
            if elapsed > (max_total * 60) + TIME_GRACE_PERIOD_SECONDS:
                return False, "Total roleplay time exceeded. Please start a new session."
    
    # Check interaction time
    if 'interaction_start_time' in session_data and 'max_interaction_time' in session_data:
        max_interaction = session_data.get('max_interaction_time', 0)
        if max_interaction > 0:  # 0 means unlimited
            interaction_elapsed = time_module.time() - session_data['interaction_start_time']
            if interaction_elapsed > (max_interaction * 60) + TIME_GRACE_PERIOD_SECONDS:
                return False, "Interaction time exceeded. Moving to next interaction."
    
    return True, None


def validate_interaction_transition(current_interaction: int, requested_interaction: int, 
                                   expected_next: int = None) -> bool:
    """
    Validate that an interaction number transition is valid.
    
    Prevents session manipulation where users try to skip or replay interactions.
    
    Args:
        current_interaction: The current interaction number
        requested_interaction: The requested next interaction number  
        expected_next: The expected next interaction (from AI flow)
        
    Returns:
        True if transition is valid, False otherwise
    """
    # Special case: -1 means completion (handled separately)
    if requested_interaction == -1:
        # -1 should only come from AI response, not from URL
        return False
    
    # If we have an expected next interaction, validate against it
    if expected_next is not None:
        return requested_interaction == expected_next
    
    # Basic sanity check: interaction should be >= 1
    if requested_interaction < 1:
        return False
    
    return True
