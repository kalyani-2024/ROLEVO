import requests
text = ("Activity 2- Roleplay - Announcing the Closure of Locations to the Team\n"
        "You have prepared to break the news to the team. You called all of them to the Area office as this is not something one could do over a conference call. "
        "All the 5 Territory Managers are now with you. They are all in a conference room now, and you have just sat down with them.\n"
        "Based on your preparation please start the discussion with them.")
char = r"C:\Users\lenovo\OneDrive\Desktop\Rolevo-flaskapp-firas\Rolevo-flaskapp-firas\data\roleplay\temp_1768067779_1768067779_TVS RP2 - Team meeting-multiparty (1).xls"
params = {'text': text, 'gender': 'male', 'character': char}
print('Requesting make_audio...')
resp = requests.get('http://127.0.0.1:5000/make_audio/', params=params)
print('Status:', resp.status_code)
print('Response (first 500 chars):')
print(resp.text[:500])
