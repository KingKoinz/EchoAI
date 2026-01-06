from pathlib import Path
import subprocess
import wave
import contextlib
import sys
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent
VIDEO_DIR = BASE_DIR / "videos"
OUTPUT_DIR = BASE_DIR / "output"
CONFIG_PATH = BASE_DIR / "config" / "settings.yaml"

AUDIO = OUTPUT_DIR / "voice.wav"
ASS_FILE = OUTPUT_DIR / "captions.ass"
FINAL_VIDEO = OUTPUT_DIR / "final.mp4"


def load_config():
    """Load settings from YAML config"""
    # Check for job-specific config first
    job_config = OUTPUT_DIR / "settings.yaml"
    config_path = job_config if job_config.exists() else CONFIG_PATH
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_audio_duration(audio_file):
    """Get duration of audio file"""
    # Use ffmpeg to get accurate duration
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
    
    # Fallback: try reading as WAV
    try:
        with contextlib.closing(wave.open(str(audio_file), 'r')) as f:
            frames = f.getnframes()
            rate = f.getframerate()
            return frames / float(rate)
    except:
        pass
    
    # Last resort: estimate from file size
    file_size = audio_file.stat().st_size
    return file_size / 88000


def find_ffmpeg():
    """Find ffmpeg executable"""
    possible_paths = [
        "ffmpeg",
        r"C:\Users\Walt\Downloads\ffmpeg\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe",
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files (x86)\HitPaw\HitPaw Watermark Remover\ffmpeg.exe",
    ]
    
    for path in possible_paths:
        try:
            subprocess.run([path, "-version"], capture_output=True, timeout=2, check=True)
            return path
        except:
            continue
    
    raise FileNotFoundError(
        "ffmpeg not found! Please add ffmpeg to your PATH or install it.\n"
        "Download from: https://ffmpeg.org/download.html"
    )


def main():
    # Get platform from command line argument
    platform = sys.argv[1] if len(sys.argv) > 1 else "tiktok"
    print(f" Rendering video with video clips for {platform}...")

    # Load config and platform specs
    config = load_config()
    platforms = config.get("platforms", {})
    platform_spec = platforms.get(platform, platforms.get("tiktok"))
    width = platform_spec.get("width", 1080)
    height = platform_spec.get("height", 1920)
    
    # Get caption style from config
    caption_style = config.get("caption_style", "bounce")
    
    print(f" Platform: {platform} ({width}x{height})")

    # Find ffmpeg executable
    ffmpeg = find_ffmpeg()

    if not AUDIO.exists():
        raise FileNotFoundError(f"Audio not found: {AUDIO}")

    # Get list of videos
    videos = sorted(VIDEO_DIR.glob("video_*.mp4"))
    if not videos:
        raise FileNotFoundError(f"No videos found in {VIDEO_DIR}")

    print(f" Found {len(videos)} video clips")

    # Get audio duration
    audio_duration = get_audio_duration(AUDIO)
    duration_per_video = audio_duration / len(videos)
    
    print(f" Audio duration: {audio_duration:.2f}s")
    print(f"  Each video clip will show for {duration_per_video:.2f}s")

    # Change to output directory so ffmpeg can find relative files
    import os
    os.chdir(OUTPUT_DIR)

    # Create a filter that processes each video clip and concatenates them
    filter_parts = []
    total_video_duration = 0
    
    for i, vid in enumerate(videos):
        # Loop video to ensure it covers the required duration, then trim
        # This ensures short videos repeat instead of ending early
        filter_parts.append(
            f"[{i}:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},setsar=1,fps=30,"
            f"loop=loop=-1:size=1:start=0,"
            f"trim=duration={duration_per_video},setpts=PTS-STARTPTS[v{i}]"
        )
        total_video_duration += duration_per_video
    
    # Check if we need to add a black screen to cover remaining audio
    remaining_time = audio_duration - total_video_duration
    if remaining_time > 0.5:  # Add black screen if more than 0.5s remaining
        print(f" Adding {remaining_time:.2f}s black screen to cover remaining audio")
        # Create a black screen segment
        filter_parts.append(
            f"color=black:s={width}x{height}:d={remaining_time}:r=30[vblack]"
        )
        num_segments = len(videos) + 1
        concat_inputs = ''.join(f"[v{i}]" for i in range(len(videos))) + "[vblack]"
    else:
        num_segments = len(videos)
        concat_inputs = ''.join(f"[v{i}]" for i in range(len(videos)))
    
    # Concatenate all video segments
    concat_filter = f"{concat_inputs}concat=n={num_segments}:v=1:a=0[video]"
    
    # Add ASS overlay only if captions enabled
    if caption_style != "none" and ASS_FILE.exists():
        ass_filter = "[video]ass=captions.ass[v]"
        full_filter = ';'.join(filter_parts + [concat_filter, ass_filter])
    else:
        # No captions - use video output directly
        full_filter = ';'.join(filter_parts + [concat_filter])
        full_filter = full_filter.replace("[video]", "[v]")

    # Build ffmpeg command with multiple video inputs
    cmd = [ffmpeg, "-y", "-nostdin"]  # -nostdin prevents keyboard input interference
    
    # Add all videos as inputs
    for vid in videos:
        cmd.extend(["-i", str(vid.absolute())])
    
    # Add audio input
    cmd.extend(["-i", str(AUDIO.absolute())])
    
    # Add filters and output options
    cmd.extend([
        "-filter_complex", full_filter,
        "-map", "[v]",
        "-map", f"{len(videos)}:a",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-t", str(audio_duration),
        "final.mp4"
    ])

    subprocess.run(cmd, check=True)

    print(f" Final TikTok video created with {len(videos)} video clips + black screen fill")


if __name__ == "__main__":
    main()
