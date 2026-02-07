"""
Script to check 16PF configuration and audio files
"""
import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

# Database connection
conn = mysql.connector.connect(
    host=os.getenv('DB_HOST', 'localhost'),
    user=os.getenv('DB_USER', 'root'),
    password=os.getenv('DB_PASSWORD'),
    database=os.getenv('DB_NAME', 'roleplay')
)
cur = conn.cursor(dictionary=True)

print("=" * 60)
print("16PF CONFIGURATION CHECK")
print("=" * 60)

# Check roleplay_config table for 16PF settings
print("\n1. Checking roleplay_config table for 16PF settings:")
cur.execute("""
    SELECT rc.roleplay_id, r.name as roleplay_name,
           rc.enable_16pf_analysis, 
           rc.pf16_analysis_source,
           rc.pf16_send_audio_for_analysis,
           rc.pf16_user_age_required,
           rc.pf16_user_gender_required,
           rc.pf16_default_age
    FROM roleplay_config rc
    LEFT JOIN roleplay r ON rc.roleplay_id = r.id
""")
configs = cur.fetchall()

if not configs:
    print("   ❌ No roleplay_config entries found!")
else:
    for cfg in configs:
        print(f"\n   Roleplay ID: {cfg['roleplay_id']} ({cfg['roleplay_name'] or 'Unknown'})")
        print(f"   - enable_16pf_analysis: {cfg['enable_16pf_analysis']}")
        print(f"   - pf16_analysis_source: {cfg['pf16_analysis_source']}")
        print(f"   - pf16_send_audio_for_analysis: {cfg['pf16_send_audio_for_analysis']}")
        
        if cfg['enable_16pf_analysis'] and cfg['pf16_send_audio_for_analysis']:
            print(f"   ✅ 16PF is ENABLED for this roleplay")
        else:
            print(f"   ❌ 16PF is DISABLED - check these flags:")
            if not cfg['enable_16pf_analysis']:
                print(f"      - enable_16pf_analysis should be 1")
            if not cfg['pf16_send_audio_for_analysis']:
                print(f"      - pf16_send_audio_for_analysis should be 1")

# Check for audio files
print("\n" + "=" * 60)
print("2. Checking for audio recordings:")

user_recordings_dir = os.path.join('app', 'static', 'user_recordings')
if os.path.exists(user_recordings_dir):
    files = os.listdir(user_recordings_dir)
    audio_files = [f for f in files if f.endswith(('.webm', '.mp3', '.wav', '.m4a', '.ogg'))]
    print(f"   Found {len(audio_files)} audio files in user_recordings/")
    if audio_files:
        print(f"   Latest 5 files:")
        for f in sorted(audio_files, reverse=True)[:5]:
            filepath = os.path.join(user_recordings_dir, f)
            size = os.path.getsize(filepath)
            print(f"      - {f} ({size} bytes)")
else:
    print(f"   ❌ user_recordings directory not found: {user_recordings_dir}")

# Check merged audio
merged_dir = os.path.join('app', 'static', 'merged_audio')
if os.path.exists(merged_dir):
    files = os.listdir(merged_dir)
    print(f"\n   Found {len(files)} files in merged_audio/")
    if files:
        for f in sorted(files, reverse=True)[:5]:
            filepath = os.path.join(merged_dir, f)
            size = os.path.getsize(filepath)
            print(f"      - {f} ({size} bytes)")
else:
    print(f"\n   ℹ️ merged_audio directory not found (will be created when first audio is merged)")

# Check 16PF analysis results
print("\n" + "=" * 60)
print("3. Checking pf16_analysis_results table:")

cur.execute("""
    SELECT id, play_id, user_id, analysis_status, audio_file_path, 
           created_at, processed_at
    FROM pf16_analysis_results
    ORDER BY id DESC
    LIMIT 5
""")
results = cur.fetchall()

if not results:
    print("   ℹ️ No 16PF analysis records found yet")
else:
    print(f"   Found {len(results)} analysis records (showing latest 5):")
    for r in results:
        print(f"\n   ID: {r['id']}, Play ID: {r['play_id']}")
        print(f"   - Status: {r['analysis_status']}")
        print(f"   - Audio: {r['audio_file_path']}")
        print(f"   - Created: {r['created_at']}")

# Check pydub/ffmpeg
print("\n" + "=" * 60)
print("4. Checking pydub and ffmpeg:")

try:
    from pydub import AudioSegment
    print("   ✅ pydub is installed")
    
    # Check if ffmpeg is available (pydub needs it for webm)
    try:
        from pydub.utils import which
        ffmpeg_path = which("ffmpeg")
        if ffmpeg_path:
            print(f"   ✅ ffmpeg found at: {ffmpeg_path}")
        else:
            print("   ⚠️ ffmpeg not found in PATH - webm conversion may fail")
            print("      Install ffmpeg: https://ffmpeg.org/download.html")
    except:
        print("   ⚠️ Could not check ffmpeg path")
except ImportError:
    print("   ❌ pydub is NOT installed - run: pip install pydub")

print("\n" + "=" * 60)
print("SQL to enable 16PF for all roleplays:")
print("-" * 60)
print("""
UPDATE roleplay_config 
SET enable_16pf_analysis = 1,
    pf16_send_audio_for_analysis = 1,
    pf16_analysis_source = 'persona360'
WHERE enable_16pf_analysis = 0;
""")

cur.close()
conn.close()
print("=" * 60)
