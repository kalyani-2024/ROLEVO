import requests
from pathlib import Path

text = ("You are meeting Mr. Melwyn, a distributor of dry-snacks. Your company ABC limited is a large producer of dry snacks which ties up distributors on a non-exclusive basis (ie you may have more than 1 distributor in 1 geographical area). This distributor has been signed up few months ago, but after the first order nothing has been re-ordered. You are now meeting Mr Melwyn in his office-cum-godown/storehouse. It is in a busy narrow street with plenty of other distributor shops for snack and other edibles. His small office is busy with 3-4 office staff loading and unloading food/related goods onto small vans. A competitor's product is being loaded as you step in.\nStart the conversation with him with the objective of getting Mr Melwyn to re-order some snacks from your company.")
char = r"C:\Users\lenovo\OneDrive\Desktop\Rolevo-flaskapp-firas\Rolevo-flaskapp-firas\data\roleplay\temp_1768132045_1768132045_Obj handling-Distributor_melwyn.xls"
params = {'text': text, 'gender': 'male', 'character': char}
print('Calling /make_audio with long scenario text...')
resp = requests.get('http://127.0.0.1:5000/make_audio/', params=params, timeout=30)
print('Status code:', resp.status_code)
print('Content-Type:', resp.headers.get('Content-Type'))
if resp.status_code == 200:
    out = Path('app') / 'temp' / 'make_audio_response.mp3'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(resp.content)
    print('Saved audio to', out)
else:
    print('Response text (truncated):')
    print(resp.text[:2000])
