import requests
import yaml

# Load config
with open('config/settings.yaml', 'r') as f:
    config = yaml.safe_load(f)

api_key = config['eleven_labs']['api_key']
voice_id = config['eleven_labs']['voice_id']

print(f"Testing Eleven Labs API...")
print(f"API Key: {api_key[:20]}...")
print(f"Voice ID: {voice_id}")

# Test the API
url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
headers = {
    "xi-api-key": api_key,
    "Content-Type": "application/json"
}
payload = {
    "text": "This is a test.",
    "model_id": "eleven_monolingual_v1",
    "voice_settings": {
        "stability": 0.5,
        "similarity_boost": 0.75
    }
}

response = requests.post(url, json=payload, headers=headers, timeout=10)

print(f"\nStatus Code: {response.status_code}")

if response.status_code == 200:
    print("✅ SUCCESS! API key and voice ID are valid.")
    print(f"Audio size: {len(response.content)} bytes")
elif response.status_code == 401:
    print("❌ FAILED: Invalid API key (401 Unauthorized)")
    print("Get a new key at: https://elevenlabs.io/app/settings/api-keys")
elif response.status_code == 404:
    print("❌ FAILED: Voice ID not found (404)")
    print("Add the voice to your library at: https://elevenlabs.io/voice-library")
else:
    print(f"❌ FAILED: {response.text}")
