import whisper
from pathlib import Path
import os
import shutil
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
AUDIO_PATH = BASE_DIR / "output" / "voice.wav"
CAPTIONS_PATH = BASE_DIR / "output" / "captions.srt"

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
        if shutil.which(path) or Path(path).exists():
            return path
    
    print(
        " ffmpeg not found! Please add ffmpeg to your PATH or install it.\n"
        "Download from: https://ffmpeg.org/download.html"
    )
    sys.exit(1)

def main():
    if not AUDIO_PATH.exists():
        raise FileNotFoundError("voice.wav not found")

    print(" Transcribing audio for captions...")
    
    # Set ffmpeg path for whisper - must be set before importing whisper's audio module
    ffmpeg_path = find_ffmpeg()
    ffmpeg_dir = str(Path(ffmpeg_path).parent)
    
    # Whisper uses this environment variable
    import whisper.audio
    whisper.audio.FFMPEG_PATH = ffmpeg_path
    
    # Also update PATH as backup
    os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")

    model = whisper.load_model("base")  # small, fast, accurate enough
    result = model.transcribe(str(AUDIO_PATH), fp16=False)

    srt_lines = []
    index = 1

    for segment in result["segments"]:
        start = segment["start"]
        end = segment["end"]
        text = segment["text"].strip()

        srt_lines.append(str(index))
        srt_lines.append(format_time(start) + " --> " + format_time(end))
        srt_lines.append(text)
        srt_lines.append("")
        index += 1

    CAPTIONS_PATH.write_text("\n".join(srt_lines), encoding="utf-8")
    print(f" Captions saved to: {CAPTIONS_PATH}")

def format_time(seconds):
    ms = int((seconds % 1) * 1000)
    s = int(seconds)
    m = s // 60
    s = s % 60
    h = m // 60
    m = m % 60
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

if __name__ == "__main__":
    main()
