"""
Render hook segment as standalone video (2 seconds)
"""
import subprocess
from pathlib import Path
import yaml
import sys
import shutil
import random

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"
IMG_DIR = BASE_DIR / "images"
VIDEO_DIR = BASE_DIR / "videos"
CONFIG_PATH = BASE_DIR / "config" / "settings.yaml"

HOOK_AUDIO = OUTPUT_DIR / "voice_hook.wav"
HOOK_TEXT = OUTPUT_DIR / "hook.txt"
HOOK_TEXT_WRAPPED = OUTPUT_DIR / "hook_wrapped.txt"
HOOK_OUTPUT = OUTPUT_DIR / "hook.mp4"

def find_ffmpeg():
    """Find ffmpeg executable"""
    paths = [
        "ffmpeg",
        r"C:\Users\Walt\Downloads\ffmpeg\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe",
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files (x86)\HitPaw\HitPaw Watermark Remover\ffmpeg.exe",
    ]
    
    for path in paths:
        if shutil.which(path):
            return path
    
    print(
        " ffmpeg not found! Please add ffmpeg to your PATH or install it.\n"
        "Download from: https://ffmpeg.org/download.html"
    )
    sys.exit(1)

def load_config():
    """Load settings from YAML config"""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def get_audio_duration(audio_file):
    """Get duration of audio file in seconds"""
    try:
        ffmpeg = find_ffmpeg()
        cmd = [ffmpeg, "-i", str(audio_file), "-f", "null", "-"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = result.stderr + result.stdout
        for line in output.split('\n'):
            if 'Duration:' in line:
                time_str = line.split('Duration:')[1].split(',')[0].strip()
                h, m, s = time_str.split(':')
                return float(h) * 3600 + float(m) * 60 + float(s)
    except:
        pass
    return 2.0  # Default fallback

def render_hook_video(platform="tiktok"):
    """Render 2-second hook segment as standalone video"""
    
    # Check if hook assets exist
    if not HOOK_TEXT.exists() or not HOOK_AUDIO.exists():
        print(" Hook assets not found (hook.txt or voice_hook.wav missing)")
        return False
    
    config = load_config()
    hook_enabled = config.get("video", {}).get("hook", {}).get("enabled", True)
    
    if not hook_enabled:
        print(" Hook disabled in settings")
        return False
    
    # Get platform specs
    platforms = config.get("platforms", {})
    platform_spec = platforms.get(platform, platforms.get("tiktok"))
    video_width = platform_spec.get("width", 1080)
    video_height = platform_spec.get("height", 1920)
    
    print(f" Rendering hook segment ({video_width}x{video_height})...")
    
    ffmpeg = find_ffmpeg()
    
    # Get background media - prefer topic-relevant images like body video
    image_files = sorted(IMG_DIR.glob("img_*.[jp][pn][g]*"))
    video_files = sorted(VIDEO_DIR.glob("video_*.mp4"))
    
    hook_cmd_start = [ffmpeg, "-y", "-nostdin"]
    
    if image_files:
        # Use first topic-relevant image (like body video does)
        hook_bg = str(image_files[0].absolute())
        hook_cmd_start.extend(["-loop", "1", "-i", hook_bg])
    elif video_files:
        # Fallback to first video if no images available
        hook_bg = str(video_files[0].absolute())
        hook_cmd_start.extend(["-i", hook_bg])
    else:
        print(" No background media found for hook")
        return False
    
    # Wrap hook text into 2 lines positioned lower on screen
    try:
        raw_hook = HOOK_TEXT.read_text(encoding="utf-8").strip()
        # Remove any non-ASCII characters to prevent box artifacts
        clean_hook = ''.join(c for c in raw_hook if 32 <= ord(c) <= 126)
        words = clean_hook.split()
        line1, line2 = [], []
        count = 0
        for w in words:
            add = len(w) + (1 if count else 0)
            if count + add <= 25:  # Balanced line lengths
                line1.append(w)
                count += add
            else:
                line2.append(w)
        wrapped = " ".join(line1)
        if line2:
            wrapped += "\n" + " ".join(line2)
        if not wrapped:
            wrapped = clean_hook
        # Write to file with proper encoding
        HOOK_TEXT_WRAPPED.write_bytes(wrapped.encode('ascii'))
    except Exception:
        clean = ''.join(c for c in HOOK_TEXT.read_text(encoding="utf-8") if 32 <= ord(c) <= 126)
        HOOK_TEXT_WRAPPED.write_bytes(clean.encode('ascii'))
    
    # Build drawtext filter - use textfile with proper line breaks
    dt = (
        "drawtext=textfile='hook_wrapped.txt':fontcolor=white:fontsize=56:"
        "font='Arial Black':x=(w-text_w)/2:y=h*0.62"
    )
    
    # Use full audio duration (don't cut off)
    hook_target = get_audio_duration(HOOK_AUDIO)
    
    # Build FFmpeg command
    hook_cmd = hook_cmd_start + [
        "-i", str(HOOK_AUDIO.absolute()),
        "-filter_complex",
        f"[0:v]scale={video_width}:{video_height}:force_original_aspect_ratio=decrease,"
        f"pad={video_width}:{video_height}:(ow-iw)/2:(oh-ih)/2:black,setsar=1,format=yuv420p,{dt}[hv]",
        "-map", "[hv]",
        "-map", "1:a",
        "-t", str(hook_target),
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        str(HOOK_OUTPUT)
    ]
    
    try:
        subprocess.run(hook_cmd, check=True, cwd=OUTPUT_DIR)
        print(f" Hook video created: {HOOK_OUTPUT}")
        return True
    except subprocess.CalledProcessError as e:
        print(f" Hook rendering failed: {e}")
        return False

def main():
    platform = sys.argv[1] if len(sys.argv) > 1 else "tiktok"
    success = render_hook_video(platform)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
