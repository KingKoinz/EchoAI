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
            result = subprocess.run([path, "-version"], capture_output=True, timeout=2)
            if result.returncode != 0:
                continue
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
    caption_style = config.get("video", {}).get("caption_style", "bounce")
    
    # Get logo overlay settings
    logo_enabled = config.get("branding", {}).get("logo", {}).get("enabled", False)
    logo_path = config.get("branding", {}).get("logo", {}).get("image_path", "")
    logo_position = config.get("branding", {}).get("logo", {}).get("position", "top_right")
    logo_width = config.get("branding", {}).get("logo", {}).get("width", 300)
    logo_padding_x = config.get("branding", {}).get("logo", {}).get("padding_x", 30)
    logo_padding_y = config.get("branding", {}).get("logo", {}).get("padding_y", 30)
    
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

    # Get target duration - prefer config setting, fallback to audio duration
    config_duration = config.get("video", {}).get("duration_seconds", None)
    
    if config_duration and AUDIO.exists():
        audio_duration = get_audio_duration(AUDIO)
        # Use whichever is longer to ensure full coverage
        target_duration = max(config_duration, audio_duration)
        print(f" Config duration: {config_duration}s, Audio duration: {audio_duration:.2f}s")
        print(f" Using target duration: {target_duration:.2f}s")
    elif config_duration:
        # No audio (skip AI mode), use config duration
        target_duration = config_duration
        print(f" No audio - using config duration: {target_duration}s")
    elif AUDIO.exists():
        # Fallback to audio duration
        target_duration = get_audio_duration(AUDIO)
        print(f" Using audio duration: {target_duration:.2f}s")
    else:
        # Last resort
        target_duration = 30
        print(f" No audio or config - using default 30s")
    
    duration_per_video = target_duration / len(videos)
    print(f"  Each video clip will show for {duration_per_video:.2f}s")

    # Change to output directory so ffmpeg can find relative files
    import os
    os.chdir(OUTPUT_DIR)

    # Create a filter that processes each video clip and concatenates them
    filter_parts = []
    total_video_duration = 0
    
    for i, vid in enumerate(videos):
        # Scale, crop, set framerate, and trim to exact duration
        # The trim will repeat the last frame if video is shorter than duration
        filter_parts.append(
            f"[{i}:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},setsar=1,fps=30,"
            f"trim=0:{duration_per_video},setpts=PTS-STARTPTS,"
            f"tpad=stop_mode=clone:stop_duration={duration_per_video}[v{i}]"
        )
        total_video_duration += duration_per_video
    
    # Check if we need to add a black screen to cover remaining audio
    remaining_time = target_duration - total_video_duration
    if remaining_time > 0.5:  # Add black screen if more than 0.5s remaining
        print(f" Adding {remaining_time:.2f}s black screen to cover remaining time")
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
    
    # Build overlay chain: video -> captions -> logo
    filter_chain = []
    current_tag = "[video]"
    
    # Add ASS overlay only if captions enabled
    if caption_style != "none" and ASS_FILE.exists():
        filter_chain.append(f"{current_tag}ass=captions.ass[vcap]")
        current_tag = "[vcap]"
    
    # Add logo overlay if enabled
    if logo_enabled and logo_path:
        logo_file = BASE_DIR / logo_path
        if logo_file.exists():
            # Calculate logo position based on setting
            if logo_position == "top_right":
                logo_x = f"W-w-{logo_padding_x}"
                logo_y = str(logo_padding_y)
            elif logo_position == "top_left":
                logo_x = str(logo_padding_x)
                logo_y = str(logo_padding_y)
            elif logo_position == "bottom_right":
                logo_x = f"W-w-{logo_padding_x}"
                logo_y = f"H-h-{logo_padding_y}"
            elif logo_position == "bottom_left":
                logo_x = str(logo_padding_x)
                logo_y = f"H-h-{logo_padding_y}"
            else:  # default top_right
                logo_x = f"W-w-{logo_padding_x}"
                logo_y = str(logo_padding_y)
            
            filter_chain.append(f"movie={str(logo_file.absolute())}:loop=0,setpts=N/(FRAME_RATE*TB),scale={logo_width}:-1[logo];{current_tag}[logo]overlay={logo_x}:{logo_y}[vlogo]")
            current_tag = "[vlogo]"
    
    # Final output tag
    if filter_chain:
        full_filter = ';'.join(filter_parts + [concat_filter] + filter_chain)
        full_filter += f";{current_tag}copy[v]"
    else:
        # No captions or logo - use video output directly
        full_filter = ';'.join(filter_parts + [concat_filter])
        full_filter = full_filter.replace("[video]", "[v]")

    # Build ffmpeg command with multiple video inputs
    cmd = [ffmpeg, "-y", "-nostdin"]  # -nostdin prevents keyboard input interference
    
    # Add all videos as inputs
    for vid in videos:
        cmd.extend(["-i", str(vid.absolute())])
    
    # Add audio input if it exists
    if AUDIO.exists():
        cmd.extend(["-i", str(AUDIO.absolute())])
        audio_index = len(videos)
    else:
        audio_index = None
    
    # Add filters and output options
    cmd.extend([
        "-filter_complex", full_filter,
        "-map", "[v]",
    ])
    
    if audio_index is not None:
        cmd.extend(["-map", f"{audio_index}:a"])
    
    cmd.extend([
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
    ])
    
    if audio_index is not None:
        cmd.extend(["-c:a", "aac", "-b:a", "128k"])
    
    cmd.extend(["-t", str(target_duration), "temp_video.mp4"])

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"FFmpeg error: {result.stderr}")
        raise RuntimeError("FFmpeg rendering failed")

    # Check if end card is enabled - TEMPORARILY DISABLED FOR DEBUGGING
    config = load_config()
    end_card_enabled = False  # config.get("branding", {}).get("end_card", {}).get("enabled", True)
    end_card_path = BASE_DIR / config.get("branding", {}).get("end_card", {}).get("image_path", "images/echo_endcard.png")
    end_card_duration = config.get("branding", {}).get("end_card", {}).get("duration", 3)
    
    if end_card_enabled and end_card_path.exists():
        print(f" Adding {end_card_duration}s end card...")
        
        # Create end card video segment
        end_card_cmd = [
            ffmpeg, "-y", "-nostdin",
            "-loop", "1",
            "-i", str(end_card_path.absolute()),
            "-t", str(end_card_duration),
            "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            "temp_endcard.mp4"
        ]
        result = subprocess.run(end_card_cmd, capture_output=True, text=True)
        print(f"✅ FIXED CLIPS ENDCARD ERROR HANDLING - Debug: Endcard FFmpeg return code: {result.returncode}")
        print(f"Debug: Endcard FFmpeg stderr length: {len(result.stderr) if result.stderr else 0}")
        
        # CRITICAL FIX: Only treat non-zero return codes as errors (FFmpeg writes progress to stderr even on success)
        if result.returncode != 0:
            print(f"❌ Actual FFmpeg clips endcard failure (code {result.returncode}): {result.stderr}")
            raise RuntimeError(f"FFmpeg endcard rendering failed (code {result.returncode}): {result.stderr}")
        else:
            print(f"✅ Clips endcard created successfully (code {result.returncode}). Stderr output is normal FFmpeg progress info.")
        
        # Concatenate main video with end card
        with open("concat_list.txt", "w") as f:
            f.write("file 'temp_video.mp4'\n")
            f.write("file 'temp_endcard.mp4'\n")
        
        concat_cmd = [
            ffmpeg, "-y", "-nostdin",
            "-f", "concat",
            "-safe", "0",
            "-i", "concat_list.txt",
            "-c", "copy",
            "final.mp4"
        ]
        print(f"Debug: Running concat command: {' '.join(concat_cmd)}")
        result = subprocess.run(concat_cmd, capture_output=True, text=True)
        print(f"Debug: Concat return code: {result.returncode}")
        print(f"Debug: Concat stderr: {result.stderr[:500] if result.stderr else 'None'}")
        if result.returncode != 0:
            print(f"FFmpeg concat error: {result.stderr}")
            # Check if temp files exist
            temp_video_exists = Path("temp_video.mp4").exists()
            temp_endcard_exists = Path("temp_endcard.mp4").exists()
            print(f"Debug: temp_video.mp4 exists: {temp_video_exists}")
            print(f"Debug: temp_endcard.mp4 exists: {temp_endcard_exists}")
    else:
        # No end card - just rename temp file to final (replace if exists)
        temp_file = Path("temp_video.mp4")
        final_file = Path("final.mp4")
        if final_file.exists():
            final_file.unlink()
        temp_file.rename(final_file)
        print(f" Final TikTok video created with {len(videos)} video clips + black screen fill")


if __name__ == "__main__":
    main()
