import os, requests, json
k = os.getenv('XI_API_KEY') or os.getenv('ELEVENLABS_API_KEY')
if not k:
    print('NO_API_KEY')
else:
    try:
        r = requests.get('https://api.elevenlabs.io/v1/voices', headers={'xi-api-key': k}, timeout=15)
        data = r.json()
    except Exception as e:
        print('ERROR', e)
        data = None
    if data is None:
        print('NO_DATA')
    else:
        with open('eleven_voices.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print('WROTE eleven_voices.json', r.status_code)
