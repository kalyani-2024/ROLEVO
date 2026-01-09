"""Test the Persona360 response parsing"""
from app.persona360_service import Persona360Service
import json

# Simulate API response (exact format from the real API)
api_response = {
    'predictions': {
        'A': 6, 'B': 6, 'C': 7, 'E': 6, 'F': 6, 'G': 8,
        'H': 5, 'I': 6, 'L': 6, 'M': 5, 'N': 5, 'O': 4,
        'Q1': 6, 'Q2': 6, 'Q3': 7, 'Q4': 7
    }
}

service = Persona360Service()
result = service._parse_response(api_response)

print('=' * 50)
print('PARSED PERSONALITY SCORES:')
print('=' * 50)
for name, score in result['personality_scores'].items():
    print(f'  {name}: {score}')

total = len(result['personality_scores'])
print(f'\nTotal traits parsed: {total}')
print(f'\nExpected: 16 traits')
print(f'Success: {total == 16}')
