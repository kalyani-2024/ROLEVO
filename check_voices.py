import pyttsx3

engine = pyttsx3.init()
voices = engine.getProperty('voices')

print(f"\n{'='*60}")
print(f"AVAILABLE VOICES ({len(voices)} total)")
print(f"{'='*60}\n")

for i, voice in enumerate(voices):
    print(f"{i+1}. {voice.name}")
    print(f"   ID: {voice.id}")
    print(f"   Languages: {voice.languages}")
    print()

print(f"{'='*60}")
print("To add more voices:")
print("Windows Settings → Time & Language → Speech → Manage voices")
print(f"{'='*60}\n")
