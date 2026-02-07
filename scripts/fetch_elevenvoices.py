import os
import json
import sys
import pathlib
import requests

# Read .env in project root
env_path = pathlib.Path(__file__).resolve().parents[1] / '.env'
if not env_path.exists():
    print('ERROR: .env not found at', env_path)
    sys.exit(1)

key = None
with open(env_path, 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if line.startswith('ELEVENLABS_API_KEY='):
            key = line.split('=', 1)[1].strip()
            break

if not key:
    print('ERROR: ELEVENLABS_API_KEY not found in .env')
    sys.exit(1)

headers = {
    'xi-api-key': key,
    'Accept': 'application/json'
}

url = 'https://api.elevenlabs.io/v1/voices'
resp = requests.get(url, headers=headers)
if resp.status_code != 200:
    print('ERROR: API call failed', resp.status_code, resp.text)
    sys.exit(1)
# Debug: print full JSON structure to inspect fields
data = resp.json()
voices = data.get('voices') or data.get('voice') or []
male = []
female = []

for v in voices:
    vid = v.get('voice_id') or v.get('id') or v.get('voiceId')
    name_raw = v.get('name') or v.get('display_name') or vid
    name = name_raw.lower().replace(' ', '_')
    gender = None
    labels = v.get('labels', {}) or v.get('metadata', {})
    gender = labels.get('gender') if isinstance(labels, dict) else None
    description = v.get('description') or name_raw

    entry = {'id': vid, 'gender': gender or 'unknown', 'description': description}
    if gender == 'male' and len(male) < 10:
        male.append((name, entry))
    elif gender == 'female' and len(female) < 10:
        female.append((name, entry))

# If not enough labeled voices, fill from unlabeled
if len(male) < 10 or len(female) < 10:
    # Fill from remaining voices regardless of label until each list has 10
    selected_ids = {e['id'] for _, e in (male + female) if e['id']}
    for v in voices:
        if len(male) >= 10 and len(female) >= 10:
            break
        vid = v.get('voice_id') or v.get('id') or v.get('voiceId')
        if not vid or vid in selected_ids:
            continue
        name_raw = v.get('name') or v.get('display_name') or vid
        name = name_raw.lower().replace(' ', '_')
        gender = (v.get('labels') or {}).get('gender') if (v.get('labels')) else None
        entry = {'id': vid, 'gender': gender or 'unknown', 'description': v.get('description') or name_raw}
        # prefer to fill female list first if female short, else male
        if len(female) < 10:
            female.append((name, entry))
        elif len(male) < 10:
            male.append((name, entry))
        selected_ids.add(vid)

mapping = {n: e for n, e in (male + female)}
print(json.dumps(mapping, indent=2))
