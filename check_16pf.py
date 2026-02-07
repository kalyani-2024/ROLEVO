from app.queries import get_16pf_analysis_by_play_id
import json

print("Checking play_id 338...")
result = get_16pf_analysis_by_play_id(338)
print("Result type:", type(result))
print("Result:", result)
if result:
    print("Status:", result.get('status'))
    print("Error:", result.get('error_message'))
    print("Has personality scores:", bool(result.get('personality_scores')))
    if result.get('personality_scores'):
        print("Personality scores:", json.dumps(result['personality_scores'], indent=2))
else:
    print("No result found for play_id 338")
