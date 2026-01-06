from pathlib import Path
import subprocess
import asyncio
import json
import yaml
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parents[1]
SCRIPT_PATH = BASE_DIR / "output" / "script.txt"
VOICE_PATH = BASE_DIR / "output" / "voice.wav"
USAGE_TRACKER = BASE_DIR / "config" / "voice_usage.json"
CONFIG_PATH = BASE_DIR / "config" / "settings.yaml"

def load_config():
    """Load settings from YAML config"""
    # Check for job-specific config first
    output_dir = BASE_DIR / "output"
    job_config = output_dir / "settings.yaml"
    config_path = job_config if job_config.exists() else CONFIG_PATH
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

MONTHLY_QUOTA = 65  # Free tier limit

def get_usage_data():
    """Load usage data from tracker file"""
    if not USAGE_TRACKER.exists():
        return {"month": datetime.now().strftime("%Y-%m"), "count": 0}
    
    try:
        data = json.loads(USAGE_TRACKER.read_text())
        current_month = datetime.now().strftime("%Y-%m")
        
        # Reset counter if new month
        if data.get("month") != current_month:
            return {"month": current_month, "count": 0}
        
        return data
    except:
        return {"month": datetime.now().strftime("%Y-%m"), "count": 0}

def update_usage():
    """Increment usage counter"""
    USAGE_TRACKER.parent.mkdir(exist_ok=True)
    data = get_usage_data()
    data["count"] += 1
    USAGE_TRACKER.write_text(json.dumps(data, indent=2))

def can_use_eleven_labs():
    """Check if we're within monthly quota"""
    config = load_config()
    api_key = config.get("eleven_labs", {}).get("api_key", "")
    
    if not api_key:
        return False
    
    data = get_usage_data()
    quota = config.get("eleven_labs", {}).get("monthly_quota", 65)
    return data["count"] < quota

async def generate_eleven_labs(text: str):
    """Generate voice using Eleven Labs API"""
    import requests
    
    config = load_config()
    api_key = config["eleven_labs"]["api_key"]
    voice_id = config["eleven_labs"]["voice_id"]
    
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json"
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",  # Better quality model
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }
    
    response = requests.post(url, json=payload, headers=headers, timeout=30)
    
    if response.status_code == 200:
        VOICE_PATH.write_bytes(response.content)
        update_usage()
        return True
    else:
        print(f"Eleven Labs failed: {response.status_code}")
        return False

async def generate_edge_tts(text: str, voice: str = "en-US-GuyNeural", rate: str = "+0%"):
    """Generate voice using Edge TTS (free unlimited)"""
    import edge_tts
    
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(str(VOICE_PATH))

def main():
    if not SCRIPT_PATH.exists():
        raise FileNotFoundError("script.txt not found. Run make_video.py first.")

    text = SCRIPT_PATH.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError("script.txt is empty.")

    # Load config for voice selection
    config = load_config()
    selected_voice = config.get("video", {}).get("voice", "en-US-GuyNeural")
    voice_rate = "+0%"
    
    # Check usage quota
    quota = config.get("eleven_labs", {}).get("monthly_quota", 65)
    usage = get_usage_data()
    remaining = quota - usage["count"]
    
    print(f"Generating voice audio...")
    print(f"Voice: {selected_voice}")
    print(f"Eleven Labs quota: {usage['count']}/{quota} used this month ({remaining} remaining)")
    
    try:
        # Try Eleven Labs if within quota
        if can_use_eleven_labs():
            print("Using Eleven Labs (premium quality)...")
            success = asyncio.run(generate_eleven_labs(text))
            
            if success:
                print(f"Voice saved to: {VOICE_PATH}")
                print(f"Premium voice used! {remaining - 1} left this month")
                return
            else:
                print("Eleven Labs failed, falling back to Edge TTS...")
        
        # Fallback to Edge TTS (free, unlimited)
        if remaining == 0:
            print("Quota reached - using Edge TTS (still great quality!)")
        else:
            print("Using Edge TTS (free unlimited backup)")
        
        import edge_tts
        asyncio.run(generate_edge_tts(text, selected_voice, voice_rate))
        print(f"Voice saved to: {VOICE_PATH}")
        
    except ImportError:
        print("edge-tts not installed. Falling back to pyttsx3...")
        print("Install with: pip install edge-tts")
        
        # Last resort: pyttsx3
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty("rate", 140)
        engine.setProperty("volume", 1.0)
        
        voices = engine.getProperty("voices")
        for voice in voices:
            if "english" in voice.name.lower():
                engine.setProperty("voice", voice.id)
                break
        
        engine.save_to_file(text, str(VOICE_PATH))
        engine.runAndWait()
        print(f"Voice saved to: {VOICE_PATH}")

if __name__ == "__main__":
    main()
