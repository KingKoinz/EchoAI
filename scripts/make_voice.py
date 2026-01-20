from pathlib import Path
import subprocess
import asyncio
import json
import yaml
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parents[1]
SCRIPT_PATH = BASE_DIR / "output" / "script.txt"
STRUCT_JSON_PATH = BASE_DIR / "output" / "script_struct.json"
HOOK_TXT_PATH = BASE_DIR / "output" / "hook.txt"
VOICE_PATH = BASE_DIR / "output" / "voice.wav"            # body voice
VOICE_HOOK_PATH = BASE_DIR / "output" / "voice_hook.wav"   # hook voice
USAGE_TRACKER = BASE_DIR / "config" / "voice_usage.json"
CONFIG_PATH = BASE_DIR / "config" / "settings.yaml"

def find_ffmpeg():
    """Find ffmpeg executable"""
    import shutil as _shutil
    paths = [
        "ffmpeg",
        r"C:\\ffmpeg\\bin\\ffmpeg.exe",
        r"C:\\Program Files\\ffmpeg\\bin\\ffmpeg.exe",
        r"C:\\Program Files (x86)\\ffmpeg\\bin\\ffmpeg.exe",
        r"C:\\Users\\Walt\\Downloads\\ffmpeg\\ffmpeg-master-latest-win64-gpl\\bin\\ffmpeg.exe",
    ]
    for p in paths:
        if _shutil.which(p):
            return p
    return "ffmpeg"  # fall back; may be on PATH

def transcode_to_pcm_wav(src: Path):
    """Transcode any audio file at src to true PCM WAV mono 48kHz, overwriting src.
    Handles cases where TTS saved MP3 with .wav extension.
    """
    if not src.exists():
        return
    ffmpeg = find_ffmpeg()
    tmp = src.with_suffix(".tmp.wav")
    try:
        subprocess.run([
            ffmpeg, "-y", "-nostdin", "-i", str(src),
            "-ac", "1", "-ar", "48000", "-sample_fmt", "s16",
            str(tmp)
        ], check=True)
        # Replace original
        src.write_bytes(tmp.read_bytes())
        tmp.unlink(missing_ok=True)
    except Exception:
        tmp.unlink(missing_ok=True)
        # If transcode fails, keep original

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

async def generate_edge_tts(text: str, out_path: Path, voice: str = "en-US-GuyNeural", rate: str = "+0%"):
    """Generate voice using Edge TTS (free unlimited)"""
    import edge_tts
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(str(out_path))

def main():
    if not SCRIPT_PATH.exists():
        raise FileNotFoundError("script.txt not found. Run make_script.py first.")

    body_text = SCRIPT_PATH.read_text(encoding="utf-8").strip()
    hook_text = HOOK_TXT_PATH.read_text(encoding="utf-8").strip() if HOOK_TXT_PATH.exists() else ""
    
    # Remove surrounding quotes if present
    if body_text.startswith('"') and body_text.endswith('"'):
        body_text = body_text[1:-1]
    
    # Remove hook text from body if hook exists
    if hook_text and body_text.startswith(hook_text):
        body_text = body_text[len(hook_text):].strip()
        print(f"Removed hook text from body (hook is {len(hook_text)} chars)")
    
    if not body_text:
        raise ValueError("script.txt is empty.")

    # Load config for voice selection
    config = load_config()
    selected_voice = config.get("video", {}).get("voice", "en-US-GuyNeural")
    voice_rate = "+0%"
    
    # Check usage quota
    quota = config.get("eleven_labs", {}).get("monthly_quota", 65)
    usage = get_usage_data()
    remaining = quota - usage["count"]
    
    print(f"Generating voice audio (hook + body)...")
    print(f"Voice: {selected_voice}")
    print(f"Eleven Labs quota: {usage['count']}/{quota} used this month ({remaining} remaining)")
    
    try:
        # Try Eleven Labs if within quota
        body_done = False
        if can_use_eleven_labs():
            print("Using Eleven Labs (premium quality) for body...")
            success = asyncio.run(generate_eleven_labs(body_text))
            if success:
                print(f"Body voice saved to: {VOICE_PATH}")
                transcode_to_pcm_wav(VOICE_PATH)
                body_done = True
            else:
                print("Eleven Labs failed for body, falling back to Edge TTS...")
        
        # Fallback to Edge TTS (free, unlimited)
        if not body_done:
            if remaining == 0:
                print("Quota reached - using Edge TTS for body")
            else:
                print("Using Edge TTS for body (backup)")
            import edge_tts
            asyncio.run(generate_edge_tts(body_text, VOICE_PATH, selected_voice, voice_rate))
            print(f"Body voice saved to: {VOICE_PATH}")
            transcode_to_pcm_wav(VOICE_PATH)

        # Generate hook voice at natural rate (no speed-up)
        if hook_text:
            print("Generating hook voice (natural rate)...")
            import edge_tts
            asyncio.run(generate_edge_tts(hook_text, VOICE_HOOK_PATH, selected_voice, "+0%"))
            print(f"Hook voice saved to: {VOICE_HOOK_PATH}")
            transcode_to_pcm_wav(VOICE_HOOK_PATH)
        
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
        
        engine.save_to_file(body_text, str(VOICE_PATH))
        engine.runAndWait()
        print(f"Voice saved to: {VOICE_PATH}")
        if hook_text:
            # pyttsx3 fallback for hook (no rate control)
            engine.save_to_file(hook_text, str(VOICE_HOOK_PATH))
            engine.runAndWait()
            print(f"Hook voice saved to: {VOICE_HOOK_PATH}")

if __name__ == "__main__":
    main()
