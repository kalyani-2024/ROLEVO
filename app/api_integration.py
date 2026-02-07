"""
AIO Integration API Module for Rolevo
Provides APIs for cluster configuration fetching and SSO authentication.
Now with JWT authentication for secure API access.
"""
import os
import secrets
import json
import hmac
import hashlib
import jwt
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, redirect, url_for, session
import mysql.connector
from dotenv import load_dotenv
from app import app, csrf

# Load environment variables from .env file
load_dotenv()

# Token storage - NOW USES DATABASE for persistence (survives server restarts)
# Format: {token: {user_id, cluster_id, expires_at, callback_url, ...}}
_integration_tokens = {}  # Memory cache only, DB is source of truth

# Token expiry time (60 minutes for SSO tokens - plenty of time)
TOKEN_EXPIRY_MINUTES = 60

# Q3 integration (Trajectorie-style assessment launch)
Q3_INTEGRATION_SECRET = os.environ.get('Q3_INTEGRATION_SECRET') or os.environ.get('AIO_CLIENT_SECRET') or os.environ.get('AIO_API_TOKEN')

# JWT Configuration
JWT_SECRET = os.environ.get('JWT_SECRET_KEY', os.environ.get('SECRET_KEY', 'fallback-jwt-secret-change-me'))
JWT_ALGORITHM = 'HS256'
JWT_EXPIRY_HOURS = 24  # JWT tokens valid for 24 hours


def generate_jwt_token(client_id, client_secret=None):
    """Generate a JWT token for API access"""
    # Validate client credentials
    expected_secret = os.environ.get('AIO_CLIENT_SECRET', os.environ.get('AIO_API_TOKEN'))
    if client_secret and expected_secret and client_secret != expected_secret:
        return None
    
    payload = {
        'client_id': client_id,
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS),
        'type': 'api_access'
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def validate_jwt_token(token):
    """Validate a JWT token and return payload"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def jwt_required(f):
    """Decorator for routes that require JWT authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Check Authorization header (Bearer token)
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        
        # Fallback to X-API-Token header (legacy support)
        if not token:
            token = request.headers.get('X-API-Token')
        
        # Fallback to query parameter
        if not token:
            token = request.args.get('api_token')
        
        if not token:
            return jsonify({'success': False, 'error': 'Authentication token required'}), 401
        
        # Try JWT validation first
        payload = validate_jwt_token(token)
        if payload:
            request.jwt_payload = payload
            return f(*args, **kwargs)
        
        # Fallback to legacy API token validation
        if validate_api_credentials(token):
            request.jwt_payload = {'client_id': 'legacy', 'type': 'api_key'}
            return f(*args, **kwargs)
        
        return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401
    
    return decorated


def validate_api_credentials(api_token):
    """Validate legacy API token against environment config"""
    # Check AIO_API_TOKEN
    expected_token = os.environ.get('AIO_API_TOKEN')
    if expected_token and api_token == expected_token:
        return True
    # Also check AIO_CLIENT_SECRET
    client_secret = os.environ.get('AIO_CLIENT_SECRET')
    if client_secret and api_token == client_secret:
        return True
    return False


def get_db_connection():
    """Get database connection"""
    return mysql.connector.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME', 'roleplay')
    )


def generate_integration_token():
    """Generate a secure random token for SSO"""
    return secrets.token_urlsafe(32)


# ===================== JWT TOKEN ENDPOINT =====================

@app.route('/api/auth/token', methods=['POST'])
@csrf.exempt
def api_get_jwt_token():
    """
    Generate a JWT token for API access.
    
    Request Body:
        {
            "client_id": "q3_platform",
            "client_secret": "your_secret_key"
        }
    
    Response:
        {
            "success": true,
            "access_token": "eyJ...",
            "token_type": "Bearer",
            "expires_in": 86400
        }
    """
    try:
        data = request.get_json() or {}
        client_id = data.get('client_id')
        client_secret = data.get('client_secret')
        
        if not client_id:
            return jsonify({'success': False, 'error': 'client_id required'}), 400
        
        if not client_secret:
            return jsonify({'success': False, 'error': 'client_secret required'}), 400
        
        # Validate credentials - check AIO_CLIENT_SECRET, AIO_API_TOKEN, or Q3_INTEGRATION_SECRET
        valid_secrets = [
            os.environ.get('AIO_CLIENT_SECRET'),
            os.environ.get('AIO_API_TOKEN'),
            os.environ.get('Q3_INTEGRATION_SECRET'),
        ]
        valid_secrets = [s for s in valid_secrets if s]  # Remove None values
        
        if not valid_secrets or client_secret not in valid_secrets:
            return jsonify({'success': False, 'error': 'Invalid credentials'}), 401
        
        # Generate JWT token
        token = generate_jwt_token(client_id, client_secret)
        if not token:
            return jsonify({'success': False, 'error': 'Failed to generate token'}), 500
        
        return jsonify({
            'success': True,
            'access_token': token,
            'token_type': 'Bearer',
            'expires_in': JWT_EXPIRY_HOURS * 3600
        }), 200
        
    except Exception as e:
        print(f"Error generating JWT token: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


def store_token(token, data):
    """Store token in DATABASE for persistence (survives server restarts)"""
    expires_at = datetime.now() + timedelta(minutes=TOKEN_EXPIRY_MINUTES)
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Insert into database
        cur.execute("""
            INSERT INTO integration_tokens 
            (token, user_id, cluster_id, callback_url, aio_user_id, user_email, expires_at, used)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 0)
            ON DUPLICATE KEY UPDATE
            cluster_id = VALUES(cluster_id),
            callback_url = VALUES(callback_url),
            aio_user_id = VALUES(aio_user_id),
            user_email = VALUES(user_email),
            expires_at = VALUES(expires_at),
            used = 0
        """, (
            token,
            data.get('user_id') if isinstance(data.get('user_id'), int) else None,
            data.get('cluster_id'),
            data.get('callback_url'),
            str(data.get('aio_user_id') or data.get('user_id') or ''),
            data.get('user_email'),
            expires_at
        ))
        conn.commit()
        cur.close()
        conn.close()
        
        # Also store extra data (user_name, return_url) in memory cache
        data['expires_at'] = expires_at
        data['created_at'] = datetime.now().isoformat()
        _integration_tokens[token] = data
        
        print(f"[SSO] Token stored in DB: {token[:20]}... expires at {expires_at}")
    except Exception as e:
        print(f"[SSO] Error storing token in DB: {e}")
        # Fallback to memory only
        data['expires_at'] = expires_at
        data['created_at'] = datetime.now().isoformat()
        _integration_tokens[token] = data


def get_token_data(token):
    """Retrieve token from DATABASE (persistent across server restarts)"""
    print(f"[SSO] Looking up token: {token[:20]}...")
    
    # First check memory cache
    if token in _integration_tokens:
        data = _integration_tokens[token]
        if datetime.now() < data['expires_at']:
            print(f"[SSO] Token found in memory cache")
            return data
    
    # Check database
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT * FROM integration_tokens 
            WHERE token = %s AND used = 0 AND expires_at > NOW()
        """, (token,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        if row:
            # Rebuild data dict from DB
            data = {
                'user_id': row.get('aio_user_id') or row.get('user_id'),
                'aio_user_id': row.get('aio_user_id'),
                'cluster_id': row.get('cluster_id'),
                'callback_url': row.get('callback_url'),
                'user_email': row.get('user_email'),
                'user_name': _integration_tokens.get(token, {}).get('user_name', ''),
                'return_url': _integration_tokens.get(token, {}).get('return_url', ''),
                'expires_at': row.get('expires_at'),
            }
            print(f"[SSO] Token found in DB, expires at {row.get('expires_at')}")
            return data
        else:
            print(f"[SSO] Token not found in DB or expired/used")
            return None
            
    except Exception as e:
        print(f"[SSO] Error reading token from DB: {e}")
        return None


def invalidate_token(token):
    """Mark token as used in database"""
    # Remove from memory cache
    if token in _integration_tokens:
        del _integration_tokens[token]
    
    # Mark as used in database
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE integration_tokens SET used = 1 WHERE token = %s", (token,))
        conn.commit()
        cur.close()
        conn.close()
        print(f"[SSO] Token invalidated in DB: {token[:20]}...")
    except Exception as e:
        print(f"[SSO] Error invalidating token: {e}")


def generate_signature(payload):
    """Generate HMAC signature for result payload"""
    secret = os.environ.get('AIO_WEBHOOK_SECRET', '')
    message = json.dumps(payload, sort_keys=True, default=str)
    signature = hmac.new(
        secret.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    return signature


def sync_cluster_metadata_to_q3(cluster_internal_id):
    """
    Build cluster metadata payload and POST to Q3 when cluster is created/updated.
    Payload matches schemas/cluster_metadata_sync.json.
    """
    import requests
    base = os.environ.get('Q3_BASE_URL', '').strip().rstrip('/')
    if not base:
        return False
    url = f"{base}/api/receive-cluster-metadata"
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT id, name, cluster_id, type FROM roleplay_cluster WHERE id = %s
        """, (cluster_internal_id,))
        cluster = cur.fetchone()
        if not cluster:
            cur.close()
            conn.close()
            return False
        cur.execute("""
            SELECT r.id, r.name, r.competency_file_path
            FROM roleplay r
            JOIN cluster_roleplay cr ON r.id = cr.roleplay_id
            WHERE cr.cluster_id = %s
            ORDER BY cr.order_sequence
        """, (cluster_internal_id,))
        roleplays = cur.fetchall()
        roleplay_list = []
        for rp in roleplays:
            cur.execute("""
                SELECT max_total_time, enable_16pf_analysis FROM roleplay_config WHERE roleplay_id = %s
            """, (rp['id'],))
            rc = cur.fetchone()
            max_total_sec = (rc['max_total_time'] or 1800) if rc else 1800
            total_time_min = max(1, max_total_sec // 60)
            enable_16pf = bool(rc.get('enable_16pf_analysis')) if rc else False
            comps = []
            try:
                cur.execute("""
                    SELECT competency_id, competency_name, max_score
                    FROM roleplay_competencies WHERE roleplay_id = %s
                """, (rp['id'],))
                rows = cur.fetchall()
            except Exception:
                rows = []
            if rows:
                for r in rows:
                    comps.append({
                        "competency_id": str(r.get('competency_id', '')),
                        "competency_name": str(r.get('competency_name', '')),
                        "max_score": int(r.get('max_score') or 3),
                    })
            elif rp.get('competency_file_path'):
                try:
                    import pandas as pd
                    p = rp['competency_file_path']
                    if os.path.exists(p):
                        df = pd.read_excel(p)
                        if 'CompetencyType' in df.columns:
                            for idx, row in df.iterrows():
                                name = row.get('CompetencyType', '')
                                if not name or not str(name).strip():
                                    continue
                                cid = row.get('CompetencyId', idx)
                                comps.append({
                                    "competency_id": str(cid).strip() if pd.notna(cid) else str(idx),
                                    "competency_name": str(name).strip(),
                                    "max_score": 3,
                                })
                except Exception:
                    pass
            roleplay_list.append({
                "roleplay_id": rp['id'],
                "roleplay_name": rp['name'],
                "total_time_minutes": total_time_min,
                "enable_16pf_analysis": enable_16pf,
                "competencies": comps,
            })
        cur.close()
        conn.close()
        payload = {
            "cluster_id": cluster['cluster_id'] or str(cluster['id']),
            "cluster_name": cluster['name'],
            "cluster_type": cluster['type'] or 'assessment',
            "number_of_roleplays": len(roleplay_list),
            "roleplays": roleplay_list,
        }
        headers = {"Content-Type": "application/json"}
        if Q3_INTEGRATION_SECRET:
            headers["Authorization"] = f"Bearer {Q3_INTEGRATION_SECRET}"
        r = requests.post(url, json=payload, headers=headers, timeout=15)
        if r.status_code in (200, 201):
            return True
        return False
    except Exception as e:
        print(f"[Q3 sync] Error syncing cluster {cluster_internal_id}: {e}")
        return False


# ===================== CLUSTER CONFIGURATION APIs =====================

@app.route('/api/rolevo/clusters', methods=['GET'])
@csrf.exempt
@jwt_required
def api_get_clusters():
    """
    Fetch all Rolevo clusters with configuration.
    Returns cluster IDs, names, roleplays, and competencies for AIO integration.
    """
    
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        
        # Get all clusters
        cur.execute("""
            SELECT id, name, cluster_id, type, created_at
            FROM roleplay_cluster
            ORDER BY name
        """)
        clusters = cur.fetchall()
        
        result = []
        for cluster in clusters:
            # Get roleplays for this cluster with competency file path
            cur.execute("""
                SELECT r.id, r.name, r.person_name, r.scenario, r.competency_file_path
                FROM roleplay r
                JOIN cluster_roleplay cr ON r.id = cr.roleplay_id
                WHERE cr.cluster_id = %s
            """, (cluster['id'],))
            roleplays = cur.fetchall()
            
            roleplay_list = []
            total_time = 0
            
            for rp in roleplays:
                competencies = []
                
                # Try to get competencies from the Excel file
                if rp.get('competency_file_path'):
                    try:
                        import pandas as pd
                        import os
                        file_path = rp['competency_file_path']
                        if os.path.exists(file_path):
                            df = pd.read_excel(file_path)
                            # Extract competencies - use CompetencyType for name, CompetencyId for ID, Abbr for code
                            if 'CompetencyType' in df.columns:
                                for idx, row in df.iterrows():
                                    comp_id = row.get('CompetencyId', idx)
                                    comp_name = row.get('CompetencyType', '')
                                    comp_code = row.get('Abbr', '')
                                    if comp_name and str(comp_name).strip():
                                        competencies.append({
                                            "competency_code": str(comp_code).strip() if pd.notna(comp_code) else '',
                                            "competency_name": str(comp_name).strip()
                                        })
                            elif 'Competency' in df.columns:
                                comp_names = df['Competency'].dropna().unique().tolist()
                                competencies = [
                                    {"competency_code": "", "competency_name": str(c)}
                                    for i, c in enumerate(comp_names) if c and str(c).strip()
                                ]
                    except Exception as e:
                        print(f"Error reading competency file: {e}")
                
                # Fallback: try dedicated table
                if not competencies:
                    try:
                        cur.execute("""
                            SELECT rc.competency_id, rc.competency_name, rc.max_score
                            FROM roleplay_competencies rc
                            WHERE rc.roleplay_id = %s
                        """, (rp['id'],))
                        competencies = cur.fetchall()
                    except:
                        pass
                
                roleplay_list.append({
                    "roleplay_id": rp['id'],
                    "roleplay_name": rp['name'],
                    "max_time_minutes": 15,
                    "competencies": competencies
                })
                total_time += 15
            
            result.append({
                "cluster_id": cluster['cluster_id'] or str(cluster['id']),
                "cluster_name": cluster['name'],
                "cluster_type": cluster['type'] or 'assessment',
                "total_roleplays": len(roleplay_list),
                "total_time_minutes": total_time,
                "roleplays": roleplay_list
            })
        
        cur.close()
        conn.close()
        
        return jsonify({"success": True, "clusters": result}), 200
        
    except Exception as e:
        print(f"Error fetching clusters: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/rolevo/cluster/<cluster_id>', methods=['GET'])
@csrf.exempt
def api_get_cluster(cluster_id):
    """Fetch specific cluster details with roleplays and competencies"""
    # Validate API token
    api_token = request.headers.get('X-API-Token') or request.args.get('api_token')
    if not validate_api_credentials(api_token):
        return jsonify({"success": False, "error": "Invalid API token"}), 401
    
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        
        # Get cluster by ID or cluster_id string
        cur.execute("""
            SELECT id, name, cluster_id, type, created_at
            FROM roleplay_cluster
            WHERE id = %s OR cluster_id = %s
        """, (cluster_id, cluster_id))
        cluster = cur.fetchone()
        
        if not cluster:
            return jsonify({"success": False, "error": "Cluster not found"}), 404
        
        # Get roleplays
        cur.execute("""
            SELECT r.id, r.name, r.person_name, r.scenario
            FROM roleplay r
            JOIN cluster_roleplay cr ON r.id = cr.roleplay_id
            WHERE cr.cluster_id = %s
        """, (cluster['id'],))
        roleplays = cur.fetchall()
        
        roleplay_list = []
        for rp in roleplays:
            # Get competencies
            cur.execute("""
                SELECT rc.competency_id, rc.competency_name, rc.max_score
                FROM roleplay_competencies rc
                WHERE rc.roleplay_id = %s
            """, (rp['id'],))
            competencies = cur.fetchall()
            
            roleplay_list.append({
                "roleplay_id": rp['id'],
                "roleplay_name": rp['name'],
                "scenario": rp['scenario'],
                "stakeholders": 1,
                "max_time_minutes": 15,
                "competencies": competencies
            })
        
        cur.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "cluster": {
                "cluster_id": cluster['cluster_id'] or str(cluster['id']),
                "cluster_name": cluster['name'],
                "total_roleplays": len(roleplay_list),
                "created_at": cluster['created_at'].isoformat() if cluster['created_at'] else None,
                "roleplays": roleplay_list
            }
        }), 200
        
    except Exception as e:
        print(f"Error fetching cluster: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ===================== SSO AUTHENTICATION APIs =====================

@app.route('/api/auth/init', methods=['POST'])
@csrf.exempt
def api_auth_init():
    """
    Initialize SSO authentication and get redirect token.
    
    Called by AIO platform to start a roleplay session.
    
    Request Body:
    {
        "api_token": "aio_api_token_here",
        "user_id": "AIO-USER-12345",  
        "user_name": "John Doe",
        "user_email": "john.doe@example.com",
        "cluster_id": "RL-SALES-2024-001",
        "callback_url": "https://aio.example.com/api/rolevo/results"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"success": False, "error": "JSON body required"}), 400
        
        api_token = data.get('api_token')
        aio_user_id = data.get('user_id')
        user_name = data.get('user_name')
        user_email = data.get('user_email')
        cluster_id = data.get('cluster_id')
        callback_url = data.get('callback_url')
        
        # Validate required fields
        if not cluster_id:
            return jsonify({
                "success": False,
                "error": "Missing required field: cluster_id"
            }), 400
        
        # Validate JWT from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"success": False, "error": "JWT token required in Authorization header"}), 401
        
        jwt_token = auth_header.split(' ')[1]
        if not validate_jwt_token(jwt_token):
            return jsonify({"success": False, "error": "Invalid or expired JWT token"}), 401
        
        # Generate session token
        token = generate_integration_token()
        
        # Find or create user in Rolevo database
        user_id = None
        if user_email:
            try:
                from app.queries import get_user_by_email, create_user
                existing_user = get_user_by_email(user_email)
                if existing_user:
                    user_id = existing_user[0]
                else:
                    # Create a new user account for this test taker
                    temp_password = secrets.token_urlsafe(16)
                    user_id, _ = create_user(user_email, temp_password, is_admin=0)
            except Exception as e:
                print(f"Error creating/finding user: {e}")
        
        # Store token data
        token_data = {
            'user_id': user_id,
            'cluster_id': cluster_id,
            'aio_user_id': aio_user_id,
            'user_name': user_name,
            'user_email': user_email,
            'callback_url': callback_url or os.environ.get('AIO_CALLBACK_URL')
        }
        store_token(token, token_data)
        
        # Build redirect URL
        base_url = request.host_url.rstrip('/')
        redirect_url = f"{base_url}/api/auth/start?token={token}&cluster_id={cluster_id}"
        
        return jsonify({
            "success": True,
            "session_token": token,
            "redirect_url": redirect_url,
            "expires_in": TOKEN_EXPIRY_MINUTES * 60
        }), 200
        
    except Exception as e:
        print(f"Error in api_auth_init: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": "Internal server error"}), 500


@app.route('/api/auth/start', methods=['GET'])
def api_auth_start():
    """
    Start roleplay session after redirect from AIO.
    
    User is redirected here with token, validates token and starts session.
    """
    token = request.args.get('token')
    cluster_id = request.args.get('cluster_id')
    
    if not token:
        return jsonify({"success": False, "error": "Token required"}), 400
    
    # Validate token
    token_data = get_token_data(token)
    if not token_data:
        return jsonify({"success": False, "error": "Invalid or expired token"}), 401
    
    # Verify cluster_id matches token data
    token_cluster = token_data.get('cluster_id')
    if str(token_cluster) != str(cluster_id):
        return jsonify({"success": False, "error": "Cluster ID mismatch"}), 400
    
    # Get external user info from token
    external_user_id = token_data.get('user_id') or token_data.get('aio_user_id')  # Q3's alphanumeric user ID
    user_name = token_data.get('user_name', '')
    user_email = token_data.get('user_email', '')
    
    print(f"[SSO] Starting session for external_user_id={external_user_id}, user_name={user_name}")
    
    # Find or create database user
    db_user_id = None
    try:
        from app.queries import get_user_by_email, create_user_account
        
        # Use user_email if provided, otherwise use user_id directly (works if it's an email or any string)
        lookup_email = user_email if user_email else external_user_id
        
        existing_user = get_user_by_email(lookup_email)
        if existing_user:
            db_user_id = existing_user[0]
            print(f"[SSO] Found existing user: {db_user_id}")
        else:
            # Create a new user account for this SSO user
            temp_password = secrets.token_urlsafe(16)
            db_user_id, _ = create_user_account(lookup_email, temp_password)
            print(f"[SSO] Created new user: {db_user_id}")
    except Exception as e:
        print(f"[SSO] Error creating/finding user: {e}")
        import traceback
        traceback.print_exc()
    
    # Fallback to user_id=1 if user creation failed
    if not db_user_id:
        db_user_id = 1
        print(f"[SSO] Fallback to db_user_id=1")
    
    # Set up session for this user
    session.clear()
    session['user_id'] = db_user_id
    session['external_user_id'] = external_user_id  # Q3's original user ID
    session['integration_token'] = token
    session['cluster_id'] = cluster_id
    session['callback_url'] = token_data.get('callback_url')
    session['user_email'] = user_email
    session['user_name'] = user_name
    session['aio_user_id'] = token_data.get('aio_user_id')
    session['is_integration_session'] = True
    session.permanent = True
    
    # Mark token as used
    invalidate_token(token)
    
    # Get cluster internal ID and redirect to cluster view
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id FROM roleplay_cluster WHERE id = %s OR cluster_id = %s", (cluster_id, cluster_id))
        cluster = cur.fetchone()
        
        if cluster:
            # Assign user to this cluster if not already assigned
            cur.execute("SELECT 1 FROM user_cluster WHERE user_id = %s AND cluster_id = %s", (db_user_id, cluster['id']))
            if not cur.fetchone():
                cur.execute("INSERT INTO user_cluster (user_id, cluster_id) VALUES (%s, %s)", (db_user_id, cluster['id']))
                conn.commit()
                print(f"[SSO] Assigned user {db_user_id} to cluster {cluster['id']}")
        
        cur.close()
        conn.close()
        
        if cluster:
            # Redirect to cluster dashboard
            return redirect(url_for('user_cluster_view', user_id=db_user_id, cluster_id=cluster['id']))
        else:
            print(f"[SSO] Cluster not found: {cluster_id}")
            return jsonify({"success": False, "error": f"Cluster not found: {cluster_id}"}), 404
            
    except Exception as e:
        print(f"[SSO] Error setting up integration session: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": f"Session setup failed: {str(e)}"}), 500


@app.route('/api/auth/validate', methods=['POST'])
@csrf.exempt
def api_auth_validate():
    """Validate a token without consuming it"""
    data = request.get_json()
    token = data.get('token') if data else None
    
    if not token:
        return jsonify({"valid": False, "error": "Token required"}), 400
    
    token_data = get_token_data(token)
    if not token_data:
        return jsonify({"valid": False}), 200
    
    expires_at = token_data.get('expires_at')
    if hasattr(expires_at, 'isoformat'):
        expires_at = expires_at.isoformat()
    
    return jsonify({
        "valid": True,
        "expires_at": str(expires_at),
        "cluster_id": token_data.get('cluster_id')
    }), 200


# ===================== Q3 ASSESSMENT LAUNCH (Trajectorie-style) =====================

def _validate_q3_jwt(auth_token):
    """Validate JWT from Q3 (assessment launch). Returns payload dict or None."""
    print(f"[Q3 JWT] Validating token...")
    print(f"[Q3 JWT] Q3_INTEGRATION_SECRET configured: {bool(Q3_INTEGRATION_SECRET)}")
    print(f"[Q3 JWT] Q3_INTEGRATION_SECRET first 10: {Q3_INTEGRATION_SECRET[:10] if Q3_INTEGRATION_SECRET else 'N/A'}")
    print(f"[Q3 JWT] auth_token provided: {bool(auth_token)}")
    if not Q3_INTEGRATION_SECRET or not auth_token:
        print(f"[Q3 JWT] Missing secret or token")
        return None
    try:
        payload = jwt.decode(auth_token, Q3_INTEGRATION_SECRET, algorithms=['HS256'])
        print(f"[Q3 JWT] Decode SUCCESS: {payload}")
        return payload
    except jwt.ExpiredSignatureError as e:
        print(f"[Q3 JWT] ExpiredSignatureError: {e}")
        return None
    except jwt.InvalidTokenError as e:
        print(f"[Q3 JWT] InvalidTokenError: {e}")
        return None


@app.route('/api/integration/assessment-launch', methods=['POST'])
@csrf.exempt
def api_integration_assessment_launch():
    """
    Assessment launch from Q3 (Trajectorie-style flow).
    Q3 POSTs user_id, user_name, assessment_cluster_id, auth_token (JWT), return_url.
    Rolevo validates JWT, creates one-time token, returns redirect_url.
    """
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id')
        user_name = data.get('user_name')
        assessment_cluster_id = data.get('assessment_cluster_id')
        auth_token = data.get('auth_token')
        return_url = data.get('return_url')
        results_url = data.get('results_url')  # optional; else Q3_BASE_URL + /api/receive-assessment-results

        required = ['user_id', 'user_name', 'assessment_cluster_id', 'auth_token', 'return_url']
        missing = [f for f in required if not data.get(f)]
        if missing:
            return jsonify({'success': False, 'detail': f'Missing required fields: {", ".join(missing)}'}), 400

        payload = _validate_q3_jwt(auth_token)
        if not payload:
            return jsonify({'success': False, 'detail': 'Authentication token is invalid or expired'}), 401
        if str(payload.get('user_id')) != str(user_id):
            return jsonify({'success': False, 'detail': 'Token user_id does not match request'}), 401
        if str(payload.get('assessment_cluster_id')) != str(assessment_cluster_id):
            return jsonify({'success': False, 'detail': 'Token assessment_cluster_id does not match request'}), 401

        from app.queries import get_cluster_by_id_or_external
        cluster = get_cluster_by_id_or_external(assessment_cluster_id)
        if not cluster:
            return jsonify({'success': False, 'detail': f'Cluster not found: {assessment_cluster_id}'}), 404

        token = generate_integration_token()
        q3_base = os.environ.get('Q3_BASE_URL', '').rstrip('/')
        callback_url = results_url or (f'{q3_base}/api/receive-assessment-results' if q3_base else None)
        store_token(token, {
            'user_id': user_id,
            'aio_user_id': user_id,
            'cluster_id': assessment_cluster_id,
            'user_name': user_name,
            'user_email': None,
            'callback_url': callback_url or os.environ.get('AIO_CALLBACK_URL'),
            'return_url': return_url,
        })

        base_url = request.host_url.rstrip('/')
        redirect_url = f"{base_url}/api/integration/assessment-start?token={token}&cluster_id={assessment_cluster_id}"

        return jsonify({
            'success': True,
            'user_id': user_id,
            'assessment_cluster_id': assessment_cluster_id,
            'redirect_url': redirect_url,
            'message': 'User authenticated successfully',
        }), 200
    except Exception as e:
        print(f"Error in assessment-launch: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'detail': 'Internal server error'}), 500


@app.route('/api/integration/assessment-start', methods=['GET', 'POST'])
@csrf.exempt
def api_integration_assessment_start():
    """
    Entry point after Q3 redirects user (GET or POST).
    Validates one-time token, creates session, redirects to cluster dashboard.
    """
    token = request.args.get('token') or (request.form.get('token') if request.method == 'POST' else None)
    cluster_id = request.args.get('cluster_id') or request.form.get('assessment_cluster_id') or request.form.get('cluster_id')

    if not token:
        return jsonify({'success': False, 'detail': 'Token required'}), 400

    token_data = get_token_data(token)
    if not token_data:
        return jsonify({'success': False, 'detail': 'Invalid or expired token'}), 401

    if cluster_id and str(token_data.get('cluster_id')) != str(cluster_id):
        return jsonify({'success': False, 'detail': 'Cluster ID mismatch'}), 400

    cluster_id = token_data.get('cluster_id')
    external_user_id = token_data.get('user_id') or token_data.get('aio_user_id')
    user_name = token_data.get('user_name', '')
    user_email = token_data.get('user_email', '')

    from app.queries import get_user_by_email, create_user_account, get_cluster_by_id_or_external

    lookup = user_email or external_user_id
    db_user_id = None
    try:
        existing = get_user_by_email(lookup)
        if existing:
            db_user_id = existing[0]
        else:
            pw = secrets.token_urlsafe(16)
            db_user_id, _ = create_user_account(lookup, pw)
    except Exception as e:
        print(f"[Assessment-start] User create/find error: {e}")
    if not db_user_id:
        db_user_id = 1

    session.clear()
    session['user_id'] = db_user_id
    session['external_user_id'] = external_user_id
    session['integration_token'] = token
    session['cluster_id'] = cluster_id
    session['callback_url'] = token_data.get('callback_url')
    session['return_url'] = token_data.get('return_url')
    session['user_email'] = user_email
    session['user_name'] = user_name
    session['aio_user_id'] = token_data.get('aio_user_id') or external_user_id
    session['is_integration_session'] = True
    session.permanent = True

    invalidate_token(token)

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id FROM roleplay_cluster WHERE id = %s OR cluster_id = %s", (cluster_id, cluster_id))
    row = cur.fetchone()
    if not row:
        cur.close()
        conn.close()
        return jsonify({'success': False, 'detail': f'Cluster not found: {cluster_id}'}), 404

    cur.execute("SELECT 1 FROM user_cluster WHERE user_id = %s AND cluster_id = %s", (db_user_id, row['id']))
    if not cur.fetchone():
        cur.execute("INSERT INTO user_cluster (user_id, cluster_id) VALUES (%s, %s)", (db_user_id, row['id']))
        conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for('user_cluster_view', user_id=db_user_id, cluster_id=row['id']))


# ===================== RESULTS CALLBACK =====================

def check_all_cluster_roleplays_completed(cluster_id, user_id):
    """
    Check if all roleplays in a cluster have been completed by the user.
    Returns True if all roleplays are done, False otherwise.
    """
    if not cluster_id or not user_id:
        print(f"[CALLBACK] check_all_cluster_roleplays_completed: missing cluster_id={cluster_id} or user_id={user_id}")
        return False
    
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        
        # Get the internal cluster ID if external ID was provided
        cur.execute("""
            SELECT id FROM roleplay_cluster 
            WHERE id = %s OR cluster_id = %s
        """, (cluster_id, cluster_id))
        cluster_row = cur.fetchone()
        
        if not cluster_row:
            print(f"[CALLBACK] Cluster not found: {cluster_id}")
            cur.close()
            conn.close()
            return False
        
        internal_cluster_id = cluster_row['id']
        
        # Get all roleplay IDs in this cluster
        cur.execute("""
            SELECT cr.roleplay_id
            FROM cluster_roleplay cr
            WHERE cr.cluster_id = %s
        """, (internal_cluster_id,))
        cluster_roleplays = cur.fetchall()
        
        if not cluster_roleplays:
            print(f"[CALLBACK] No roleplays in cluster {cluster_id}")
            cur.close()
            conn.close()
            return False
        
        roleplay_ids = [r['roleplay_id'] for r in cluster_roleplays]
        total_roleplays = len(roleplay_ids)
        
        # Count how many roleplays the user has completed in this cluster
        placeholders = ','.join(['%s'] * len(roleplay_ids))
        cur.execute(f"""
            SELECT COUNT(DISTINCT roleplay_id) as completed_count
            FROM play
            WHERE user_id = %s 
              AND cluster_id = %s
              AND roleplay_id IN ({placeholders})
              AND status IN ('completed', 'optimal_viewed')
        """, (user_id, internal_cluster_id, *roleplay_ids))
        
        result = cur.fetchone()
        completed_count = result['completed_count'] if result else 0
        
        cur.close()
        conn.close()
        
        print(f"[CALLBACK] Cluster {cluster_id}: {completed_count}/{total_roleplays} roleplays completed by user {user_id}")
        
        return completed_count >= total_roleplays
        
    except Exception as e:
        print(f"[CALLBACK] Error checking cluster completion: {e}")
        import traceback
        traceback.print_exc()
        return False


def send_results_to_aio(play_id, user_id, roleplay_id, scores):
    """
    Send roleplay results back to AIO/Q3 platform.

    Results are always POSTed to the callback URL from the launch flow:
    - Integration (assessment-launch): callback_url stored in session (from results_url
      in the launch request, or Q3_BASE_URL + /api/receive-assessment-results, or
      AIO_CALLBACK_URL). We never use Q3_BASE_URL directly here.
    - Legacy (auth/init): callback_url from init request or AIO_CALLBACK_URL.

    Called after a roleplay is completed.
    """
    try:
        callback_url = session.get('callback_url') or os.environ.get('AIO_CALLBACK_URL')
        
        print(f"[CALLBACK] Attempting to send results...")
        print(f"[CALLBACK] play_id={play_id}, user_id={user_id}, roleplay_id={roleplay_id}")
        print(f"[CALLBACK] callback_url from session: {session.get('callback_url')}")
        print(f"[CALLBACK] callback_url from env: {os.environ.get('AIO_CALLBACK_URL')}")
        print(f"[CALLBACK] Final callback_url: {callback_url}")
        
        if not callback_url:
            print("[CALLBACK] No callback URL configured, skipping result callback")
            return False
        
        # Build result payload
        result_payload = build_result_payload(play_id, user_id, roleplay_id, scores)
        print(f"[CALLBACK] Payload: {result_payload}")
        
        # Send to callback URL
        import requests
        print(f"[CALLBACK] Sending POST to {callback_url}...")
        response = requests.post(
            callback_url,
            json=result_payload,
            headers={
                'Content-Type': 'application/json',
                'X-Rolevo-Signature': generate_signature(result_payload)
            },
            timeout=30
        )
        
        if response.ok:
            print(f"[CALLBACK] ✅ Results sent successfully: {response.status_code}")
            return True
        else:
            print(f"[CALLBACK] ❌ Failed to send results: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"[CALLBACK] ❌ Error sending results: {e}")
        import traceback
        traceback.print_exc()
        return False


def _slug_code(name, idx):
    """Alphanumeric code from competency name for Q3 competency_code."""
    if not name:
        return f"C{idx:02d}"
    # Remove spaces and special chars, keep full name (no truncation)
    s = "".join(c for c in str(name).upper() if c.isalnum())
    return s or f"C{idx:02d}"


def build_result_payload(play_id, user_id, roleplay_id, scores):
    """Build result JSON for ALL completed roleplays in the cluster (Q3 format: results_submission.json)."""
    from app.queries import (get_play_info, query_showreport, get_user, get_roleplay, 
                             get_cluster_by_id_or_external, get_16pf_analysis_by_play_id,
                             get_16pf_config_for_roleplay)

    user = get_user(user_id) if user_id else None
    cluster_id_val = session.get('cluster_id')
    cluster = get_cluster_by_id_or_external(cluster_id_val) if cluster_id_val else None

    cluster_type = 'assessment'
    cluster_name = None
    external_cluster_id = cluster_id_val
    if cluster:
        if len(cluster) > 3 and cluster[3]:
            cluster_type = cluster[3]
        cluster_name = cluster[1]
        if len(cluster) > 2 and cluster[2]:
            external_cluster_id = cluster[2]

    # Get ALL completed plays for this user in this cluster
    all_roleplay_results = []
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        
        # Get internal cluster ID
        cur.execute("SELECT id FROM roleplay_cluster WHERE id = %s OR cluster_id = %s", (cluster_id_val, cluster_id_val))
        cluster_row = cur.fetchone()
        internal_cluster_id = cluster_row['id'] if cluster_row else None
        
        if internal_cluster_id:
            # Get all completed plays for this user in this cluster
            cur.execute("""
                SELECT DISTINCT p.id as play_id, p.roleplay_id, p.start_time, p.end_time,
                       r.name as roleplay_name
                FROM play p
                JOIN roleplay r ON p.roleplay_id = r.id
                WHERE p.user_id = %s 
                  AND p.cluster_id = %s
                  AND p.status IN ('completed', 'optimal_viewed')
                ORDER BY p.roleplay_id, p.end_time DESC
            """, (user_id, internal_cluster_id))
            completed_plays = cur.fetchall()
            
            # Group by roleplay_id (take latest play per roleplay)
            seen_roleplays = set()
            for play in completed_plays:
                rp_id = play['roleplay_id']
                if rp_id in seen_roleplays:
                    continue
                seen_roleplays.add(rp_id)
                
                # Get config for this roleplay
                cur.execute("SELECT max_total_time, enable_16pf_analysis FROM roleplay_config WHERE roleplay_id = %s", (rp_id,))
                config_row = cur.fetchone()
                max_time_seconds = (config_row['max_total_time'] or 1800) if config_row else 1800
                enable_16pf = bool(config_row.get('enable_16pf_analysis')) if config_row else False
                max_time_minutes = max_time_seconds // 60
                
                # Calculate duration
                duration_minutes = 0
                if play['start_time'] and play['end_time']:
                    duration_seconds = int((play['end_time'] - play['start_time']).total_seconds())
                    duration_minutes = duration_seconds // 60
                
                # Get competency scores from report
                report = query_showreport(play['play_id'])
                competency_scores = []
                total_marks_obtained = 0
                total_max_marks = 0
                if report and report[1]:
                    for idx, comp in enumerate(report[1]):
                        if not isinstance(comp, dict):
                            continue
                        name = comp.get('name', 'Unknown')
                        marks = int(comp.get('score', 0))
                        total = int(comp.get('total_possible', 3))
                        code = _slug_code(name, idx)
                        competency_scores.append({
                            "competency_code": code,
                            "competency_name": name,
                            "max_marks": total,
                            "marks_obtained": marks,
                        })
                        total_marks_obtained += marks
                        total_max_marks += total
                
                # Calculate percentage
                percentage = round((total_marks_obtained / total_max_marks * 100), 2) if total_max_marks > 0 else 0
                
                # Build roleplay result object
                roleplay_result = {
                    "roleplay_id": rp_id,
                    "roleplay_name": play['roleplay_name'],
                    "stakeholders": "01",
                    "max_time": max_time_minutes,
                    "time_taken": duration_minutes,
                    "total_score": total_marks_obtained,
                    "max_score": total_max_marks,
                    "percentage": percentage,
                    "competencies": competency_scores,
                }
                
                # Include 16PF raw results if enabled
                if enable_16pf:
                    pf16_result = get_16pf_analysis_by_play_id(play['play_id'])
                    if pf16_result and pf16_result.get('status') == 'completed':
                        roleplay_result["16pf_analysis"] = pf16_result.get('raw_response')
                
                all_roleplay_results.append(roleplay_result)
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"[CALLBACK] Error building payload for all roleplays: {e}")
        import traceback
        traceback.print_exc()

    payload = {
        "cluster_id": external_cluster_id,
        "cluster_name": cluster_name,
        "cluster_type": cluster_type,
        "user_id": session.get('aio_user_id') or (str(user[0]) if user else None),
        "user_name": session.get('user_name') or (user[1] if user and len(user) > 1 else ''),
        "roleplays": all_roleplay_results,
    }
    return payload


# ===================== SCORES FETCH APIs =====================

@app.route('/api/rolevo/scores/cluster/<cluster_id>', methods=['GET'])
@csrf.exempt
@jwt_required
def api_get_scores_by_cluster(cluster_id):
    """Fetch all scores for a cluster grouped by user and roleplay"""
    
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        
        # Get cluster info
        cur.execute("SELECT id, name, cluster_id FROM roleplay_cluster WHERE cluster_id = %s OR id = %s", (cluster_id, cluster_id))
        cluster = cur.fetchone()
        if not cluster:
            return jsonify({"success": False, "error": "Cluster not found"}), 404
        
        # Get all completed plays for this cluster
        cur.execute("""
            SELECT p.id as play_id, p.user_id, p.roleplay_id, p.status, p.start_time, p.end_time,
                   u.email as user_email, r.name as roleplay_name
            FROM play p
            LEFT JOIN user u ON p.user_id = u.id
            LEFT JOIN roleplay r ON p.roleplay_id = r.id
            WHERE p.cluster_id = %s AND p.status IN ('completed', 'optimal_viewed')
            ORDER BY u.email, p.roleplay_id, p.end_time DESC
        """, (cluster['id'],))
        plays = cur.fetchall()
        
        # Group by user, then by roleplay
        users = {}
        for play in plays:
            user_key = play['user_email'] or f"user_{play['user_id']}"
            rp_id = play['roleplay_id']
            
            if user_key not in users:
                users[user_key] = {"user_id": play['user_email'], "roleplays": {}}
            
            if rp_id not in users[user_key]['roleplays']:
                # Get interaction count and scores
                cur.execute("SELECT COUNT(*) as count FROM chathistory WHERE play_id = %s", (play['play_id'],))
                interaction_count = cur.fetchone()['count']
                
                cur.execute("""
                    SELECT sb.score_name as competency, sb.score, sm.overall_score
                    FROM scorebreakdown sb
                    JOIN scoremaster sm ON sb.scoremaster_id = sm.id
                    JOIN chathistory ch ON sm.chathistory_id = ch.id
                    WHERE ch.play_id = %s
                """, (play['play_id'],))
                score_rows = cur.fetchall()
                
                competencies = {}
                overall_score = 0
                for row in score_rows:
                    comp = row['competency']
                    if comp not in competencies:
                        competencies[comp] = {'score': 0, 'count': 0, 'max_score': 3}
                    competencies[comp]['score'] += row['score']
                    competencies[comp]['count'] += 1
                    if row['overall_score']:
                        overall_score = row['overall_score']
                
                # Calculate time taken
                time_taken_seconds = None
                if play.get('start_time') and play.get('end_time'):
                    time_taken_seconds = int((play['end_time'] - play['start_time']).total_seconds())
                
                users[user_key]['roleplays'][rp_id] = {
                    "roleplay_id": rp_id,
                    "roleplay_name": play['roleplay_name'],
                    "total_interactions": interaction_count,
                    "overall_score": overall_score,
                    "time_taken_seconds": time_taken_seconds,
                    "competencies": [
                        {
                            "competency_code": k.split()[0] if k else "",
                            "competency_name": k,
                            "max_score": v['max_score'] * v['count'],
                            "score_obtained": v['score']
                        }
                        for k, v in competencies.items()
                    ],
                    "completed_at": play['end_time'].isoformat() if play['end_time'] else None
                }
        
        # Format response
        result = []
        for user_key, user_data in users.items():
            result.append({
                "user_id": user_data['user_id'],
                "roleplays": list(user_data['roleplays'].values())
            })
        
        cur.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "cluster_id": cluster['cluster_id'],
            "cluster_name": cluster['name'],
            "cluster_type": cluster.get('type') or 'assessment',
            "total_users": len(result),
            "users": result
        })
        
    except Exception as e:
        print(f"Error fetching scores: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/rolevo/scores/user/<user_id>', methods=['GET'])
@csrf.exempt
@jwt_required
def api_get_scores_by_user(user_id):
    """Fetch all scores for a user grouped by roleplay with competency breakdowns"""
    
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        
        # Find user by ID or email
        cur.execute("SELECT id, email FROM user WHERE id = %s OR email = %s", (user_id, user_id))
        user = cur.fetchone()
        if not user:
            return jsonify({"success": False, "error": "User not found"}), 404
        
        # Get all completed plays for this user (distinct by roleplay)
        cur.execute("""
            SELECT p.id as play_id, p.cluster_id, p.roleplay_id, p.status, p.start_time, p.end_time,
                   r.name as roleplay_name, rc.name as cluster_name, rc.cluster_id as external_cluster_id,
                   rc.type as cluster_type
            FROM play p
            LEFT JOIN roleplay r ON p.roleplay_id = r.id
            LEFT JOIN roleplay_cluster rc ON p.cluster_id = rc.id
            WHERE p.user_id = %s AND p.status IN ('completed', 'optimal_viewed')
            ORDER BY p.end_time DESC
        """, (user['id'],))
        plays = cur.fetchall()
        
        # Group plays by roleplay and get detailed scores
        roleplays = {}
        for play in plays:
            rp_id = play['roleplay_id']
            if rp_id not in roleplays:
                # Get interaction count
                cur.execute("SELECT COUNT(*) as count FROM chathistory WHERE play_id = %s", (play['play_id'],))
                interaction_count = cur.fetchone()['count']
                
                # Get competency scores for this play
                cur.execute("""
                    SELECT sb.score_name as competency, sb.score, sm.overall_score
                    FROM scorebreakdown sb
                    JOIN scoremaster sm ON sb.scoremaster_id = sm.id
                    JOIN chathistory ch ON sm.chathistory_id = ch.id
                    WHERE ch.play_id = %s
                """, (play['play_id'],))
                score_rows = cur.fetchall()
                
                # Aggregate competency scores
                competencies = {}
                overall_score = 0
                for row in score_rows:
                    comp = row['competency']
                    if comp not in competencies:
                        competencies[comp] = {'score': 0, 'count': 0, 'max_score': 3}
                    competencies[comp]['score'] += row['score']
                    competencies[comp]['count'] += 1
                    if row['overall_score']:
                        overall_score = row['overall_score']
                
                # Format competencies as list with code, name, max_score, score_obtained
                competency_list = [
                    {
                        "competency_code": k.split()[0] if k else "",  # First word as code
                        "competency_name": k,
                        "max_score": v['max_score'] * v['count'],  # max per interaction * interactions
                        "score_obtained": v['score'],
                        "interactions": v['count']
                    }
                    for k, v in competencies.items()
                ]
                
                # Calculate time taken
                time_taken_seconds = None
                if play['start_time'] and play['end_time']:
                    time_taken_seconds = int((play['end_time'] - play['start_time']).total_seconds())
                
                roleplays[rp_id] = {
                    "roleplay_id": rp_id,
                    "roleplay_name": play['roleplay_name'],
                    "cluster_id": play['external_cluster_id'],
                    "cluster_name": play['cluster_name'],
                    "cluster_type": play.get('cluster_type') or 'assessment',
                    "play_id": play['play_id'],
                    "status": play['status'],
                    "start_time": play['start_time'].isoformat() if play['start_time'] else None,
                    "end_time": play['end_time'].isoformat() if play['end_time'] else None,
                    "time_taken_seconds": time_taken_seconds,
                    "total_interactions": interaction_count,
                    "overall_score": overall_score,
                    "competencies": competency_list
                }
        
        cur.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "user_id": user_id,
            "user_email": user['email'],
            "total_roleplays": len(roleplays),
            "roleplays": list(roleplays.values())
        })
        
    except Exception as e:
        print(f"Error fetching scores: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/rolevo/scores/play/<int:play_id>', methods=['GET'])
@csrf.exempt
@jwt_required
def api_get_scores_by_play(play_id):
    """Fetch detailed scores for a specific play session"""
    
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        
        # Get play details
        cur.execute("""
            SELECT p.*, u.email as user_email, r.name as roleplay_name, rc.cluster_id as external_cluster_id
            FROM play p
            LEFT JOIN user u ON p.user_id = u.id
            LEFT JOIN roleplay r ON p.roleplay_id = r.id
            LEFT JOIN roleplay_cluster rc ON p.cluster_id = rc.id
            WHERE p.id = %s
        """, (play_id,))
        play = cur.fetchone()
        
        if not play:
            return jsonify({"success": False, "error": "Play not found"}), 404
        
        # Get score breakdown
        cur.execute("""
            SELECT sb.competency, sb.score, sm.overall_score
            FROM scorebreakdown sb
            JOIN scoremaster sm ON sb.scoremaster_id = sm.id
            JOIN chathistory ch ON sm.chathistory_id = ch.id
            WHERE ch.play_id = %s
        """, (play_id,))
        scores = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "play": play,
            "scores": scores
        })
        
    except Exception as e:
        print(f"Error fetching scores: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ===================== DEBUG ENDPOINT (remove after testing) =====================

@app.route('/api/integration/debug-secret', methods=['GET'])
@csrf.exempt
def api_debug_secret():
    """Temporary debug endpoint to check Q3 secret configuration"""
    secret = Q3_INTEGRATION_SECRET
    if not secret:
        return jsonify({
            "configured": False,
            "message": "Q3_INTEGRATION_SECRET is not set"
        })
    return jsonify({
        "configured": True,
        "secret_length": len(secret),
        "secret_first_10": secret[:10],
        "secret_last_5": secret[-5:]
    })


@app.route('/api/integration/debug-results/<cluster_id>/<int:user_id>', methods=['GET'])
@csrf.exempt
def api_debug_results(cluster_id, user_id):
    """
    Debug endpoint to view the result payload that would be sent to callback.
    Usage: /api/integration/debug-results/<cluster_id>/<user_id>
    """
    try:
        from app.queries import get_user, get_cluster_by_id_or_external, get_16pf_analysis_by_play_id
        
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        
        # Get cluster info
        cur.execute("SELECT id, name, cluster_id, type FROM roleplay_cluster WHERE id = %s OR cluster_id = %s", (cluster_id, cluster_id))
        cluster = cur.fetchone()
        if not cluster:
            return jsonify({"error": f"Cluster not found: {cluster_id}"}), 404
        
        internal_cluster_id = cluster['id']
        external_cluster_id = cluster['cluster_id'] or str(cluster['id'])
        cluster_name = cluster['name']
        cluster_type = cluster['type'] or 'assessment'
        
        # Get user info
        user = get_user(user_id)
        user_email = user[1] if user and len(user) > 1 else ''
        
        # Get all completed plays for this user in this cluster
        cur.execute("""
            SELECT DISTINCT p.id as play_id, p.roleplay_id, p.start_time, p.end_time,
                   r.name as roleplay_name
            FROM play p
            JOIN roleplay r ON p.roleplay_id = r.id
            WHERE p.user_id = %s 
              AND p.cluster_id = %s
              AND p.status IN ('completed', 'optimal_viewed')
            ORDER BY p.roleplay_id, p.end_time DESC
        """, (user_id, internal_cluster_id))
        completed_plays = cur.fetchall()
        
        if not completed_plays:
            return jsonify({
                "error": "No completed roleplays found",
                "cluster_id": external_cluster_id,
                "user_id": user_id
            }), 404
        
        # Build roleplay results
        all_roleplay_results = []
        seen_roleplays = set()
        
        for play in completed_plays:
            rp_id = play['roleplay_id']
            if rp_id in seen_roleplays:
                continue
            seen_roleplays.add(rp_id)
            
            # Get config
            cur.execute("SELECT max_total_time, enable_16pf_analysis FROM roleplay_config WHERE roleplay_id = %s", (rp_id,))
            config_row = cur.fetchone()
            max_time_seconds = (config_row['max_total_time'] or 1800) if config_row else 1800
            enable_16pf = bool(config_row.get('enable_16pf_analysis')) if config_row else False
            max_time_minutes = max_time_seconds // 60
            
            # Calculate duration
            duration_minutes = 0
            if play['start_time'] and play['end_time']:
                duration_seconds = int((play['end_time'] - play['start_time']).total_seconds())
                duration_minutes = duration_seconds // 60
            
            # Get competency scores
            from app.queries import query_showreport
            report = query_showreport(play['play_id'])
            competency_scores = []
            total_marks_obtained = 0
            total_max_marks = 0
            if report and report[1]:
                for idx, comp in enumerate(report[1]):
                    if not isinstance(comp, dict):
                        continue
                    name = comp.get('name', 'Unknown')
                    marks = int(comp.get('score', 0))
                    total = int(comp.get('total_possible', 3))
                    code = _slug_code(name, idx)
                    competency_scores.append({
                        "competency_code": code,
                        "competency_name": name,
                        "max_marks": total,
                        "marks_obtained": marks,
                    })
                    total_marks_obtained += marks
                    total_max_marks += total
            
            # Calculate percentage
            percentage = round((total_marks_obtained / total_max_marks * 100), 2) if total_max_marks > 0 else 0
            
            roleplay_result = {
                "roleplay_id": rp_id,
                "roleplay_name": play['roleplay_name'],
                "stakeholders": "01",
                "max_time": max_time_minutes,
                "time_taken": duration_minutes,
                "total_score": total_marks_obtained,
                "max_score": total_max_marks,
                "percentage": percentage,
                "competencies": competency_scores,
            }
            
            # 16PF if enabled
            if enable_16pf:
                pf16_result = get_16pf_analysis_by_play_id(play['play_id'])
                if pf16_result and pf16_result.get('status') == 'completed':
                    roleplay_result["16pf_analysis"] = pf16_result.get('raw_response')
            
            all_roleplay_results.append(roleplay_result)
        
        cur.close()
        conn.close()
        
        payload = {
            "cluster_id": external_cluster_id,
            "cluster_name": cluster_name,
            "cluster_type": cluster_type,
            "user_id": str(user_id),
            "user_name": user_email,
            "roleplays": all_roleplay_results,
        }
        
        return jsonify(payload), 200
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/integration/debug-session', methods=['GET'])
@csrf.exempt
def api_debug_session():
    """Debug endpoint to check what's stored in the current session"""
    return jsonify({
        "user_id": session.get('user_id'),
        "external_user_id": session.get('external_user_id'),
        "cluster_id": session.get('cluster_id'),
        "callback_url": session.get('callback_url'),
        "return_url": session.get('return_url'),
        "aio_user_id": session.get('aio_user_id'),
        "is_integration_session": session.get('is_integration_session'),
        "user_email": session.get('user_email'),
        "user_name": session.get('user_name'),
    }), 200


@app.route('/api/integration/test-callback', methods=['POST'])
@csrf.exempt
def api_test_callback():
    """
    Test endpoint to manually trigger a callback to verify receive-assessment-results works.
    
    POST body:
    {
        "cluster_id": "6650b144-3dc",
        "user_id": 22,
        "callback_url": "https://webhook.site/xxx"
    }
    """
    import requests as req
    
    data = request.get_json() or {}
    cluster_id = data.get('cluster_id')
    user_id = data.get('user_id')
    callback_url = data.get('callback_url')
    
    if not all([cluster_id, user_id, callback_url]):
        return jsonify({"error": "Missing required fields: cluster_id, user_id, callback_url"}), 400
    
    try:
        from app.queries import get_user, get_16pf_analysis_by_play_id, query_showreport
        
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        
        # Get cluster info
        cur.execute("SELECT id, name, cluster_id, type FROM roleplay_cluster WHERE id = %s OR cluster_id = %s", (cluster_id, cluster_id))
        cluster = cur.fetchone()
        if not cluster:
            return jsonify({"error": f"Cluster not found: {cluster_id}"}), 404
        
        internal_cluster_id = cluster['id']
        external_cluster_id = cluster['cluster_id'] or str(cluster['id'])
        cluster_name = cluster['name']
        cluster_type = cluster['type'] or 'assessment'
        
        # Get user info
        user = get_user(user_id)
        user_email = user[1] if user and len(user) > 1 else ''
        
        # Get all completed plays
        cur.execute("""
            SELECT DISTINCT p.id as play_id, p.roleplay_id, p.start_time, p.end_time,
                   r.name as roleplay_name
            FROM play p
            JOIN roleplay r ON p.roleplay_id = r.id
            WHERE p.user_id = %s 
              AND p.cluster_id = %s
              AND p.status IN ('completed', 'optimal_viewed')
            ORDER BY p.roleplay_id, p.end_time DESC
        """, (user_id, internal_cluster_id))
        completed_plays = cur.fetchall()
        
        if not completed_plays:
            return jsonify({"error": "No completed roleplays found"}), 404
        
        # Build roleplay results
        all_roleplay_results = []
        seen_roleplays = set()
        
        for play in completed_plays:
            rp_id = play['roleplay_id']
            if rp_id in seen_roleplays:
                continue
            seen_roleplays.add(rp_id)
            
            cur.execute("SELECT max_total_time, enable_16pf_analysis FROM roleplay_config WHERE roleplay_id = %s", (rp_id,))
            config_row = cur.fetchone()
            max_time_seconds = (config_row['max_total_time'] or 1800) if config_row else 1800
            enable_16pf = bool(config_row.get('enable_16pf_analysis')) if config_row else False
            max_time_minutes = max_time_seconds // 60
            
            duration_minutes = 0
            if play['start_time'] and play['end_time']:
                duration_seconds = int((play['end_time'] - play['start_time']).total_seconds())
                duration_minutes = duration_seconds // 60
            
            report = query_showreport(play['play_id'])
            competency_scores = []
            total_marks_obtained = 0
            total_max_marks = 0
            if report and report[1]:
                for idx, comp in enumerate(report[1]):
                    if not isinstance(comp, dict):
                        continue
                    name = comp.get('name', 'Unknown')
                    marks = int(comp.get('score', 0))
                    total = int(comp.get('total_possible', 3))
                    code = _slug_code(name, idx)
                    competency_scores.append({
                        "competency_code": code,
                        "competency_name": name,
                        "max_marks": total,
                        "marks_obtained": marks,
                    })
                    total_marks_obtained += marks
                    total_max_marks += total
            
            # Calculate percentage
            percentage = round((total_marks_obtained / total_max_marks * 100), 2) if total_max_marks > 0 else 0
            
            roleplay_result = {
                "roleplay_id": rp_id,
                "roleplay_name": play['roleplay_name'],
                "stakeholders": "01",
                "max_time": max_time_minutes,
                "time_taken": duration_minutes,
                "total_score": total_marks_obtained,
                "max_score": total_max_marks,
                "percentage": percentage,
                "competencies": competency_scores,
            }
            
            if enable_16pf:
                pf16_result = get_16pf_analysis_by_play_id(play['play_id'])
                if pf16_result and pf16_result.get('status') == 'completed':
                    roleplay_result["16pf_analysis"] = pf16_result.get('raw_response')
            
            all_roleplay_results.append(roleplay_result)
        
        cur.close()
        conn.close()
        
        # Build payload matching results_submission.json schema
        payload = {
            "cluster_id": external_cluster_id,
            "cluster_name": cluster_name,
            "cluster_type": cluster_type,
            "user_id": str(user_id),
            "user_name": user_email,
            "roleplays": all_roleplay_results,
        }
        
        # POST to callback URL (simulating what Q3's /api/receive-assessment-results would receive)
        print(f"[TEST-CALLBACK] Sending POST to {callback_url}")
        print(f"[TEST-CALLBACK] Payload: {payload}")
        
        response = req.post(
            callback_url,
            json=payload,
            headers={
                'Content-Type': 'application/json',
                'X-Rolevo-Signature': generate_signature(payload)
            },
            timeout=30
        )
        
        return jsonify({
            "success": True,
            "callback_url": callback_url,
            "callback_status": response.status_code,
            "callback_response": response.text[:500] if response.text else "",
            "payload_sent": payload
        }), 200
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/integration/debug-jwt', methods=['POST'])
@csrf.exempt
def api_debug_jwt():
    """Debug endpoint to test JWT validation"""
    from datetime import datetime
    data = request.get_json() or {}
    auth_token = data.get('auth_token')
    
    if not auth_token:
        return jsonify({"error": "No auth_token provided"}), 400
    
    secret = Q3_INTEGRATION_SECRET
    if not secret:
        return jsonify({"error": "Q3_INTEGRATION_SECRET not configured"}), 500
    
    # Get server time info
    now = datetime.utcnow()
    now_ts = int(now.timestamp())
    
    try:
        # First try without verification to see the payload
        unverified = jwt.decode(auth_token, options={"verify_signature": False, "verify_exp": False})
        
        # Now try with verification
        payload = jwt.decode(auth_token, secret, algorithms=['HS256'])
        return jsonify({
            "valid": True,
            "payload": payload,
            "server_time": now.isoformat(),
            "server_timestamp": now_ts
        })
    except jwt.ExpiredSignatureError as e:
        return jsonify({
            "valid": False, 
            "error": "ExpiredSignatureError", 
            "message": str(e),
            "server_time": now.isoformat(),
            "server_timestamp": now_ts,
            "token_payload_unverified": unverified if 'unverified' in dir() else None
        })
    except jwt.InvalidTokenError as e:
        return jsonify({
            "valid": False, 
            "error": "InvalidTokenError", 
            "message": str(e),
            "server_time": now.isoformat(),
            "server_timestamp": now_ts
        })


# Register the module's routes when imported
print("[API Integration] AIO Integration APIs loaded")
