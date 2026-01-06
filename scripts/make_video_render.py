from pathlib import Path
import subprocess
import wave
import contextlib

BASE_DIR = Path(__file__).resolve().parent.parent
IMG_DIR = BASE_DIR / "images"
OUTPUT_DIR = BASE_DIR / "output"

AUDIO = OUTPUT_DIR / "voice.wav"
ASS_FILE = OUTPUT_DIR / "captions.ass"
FINAL_VIDEO = OUTPUT_DIR / "final.mp4"


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
    import sys
    
    # Get platform from command line argument (default to tiktok)
    platform = sys.argv[1] if len(sys.argv) > 1 else "tiktok"
    
    print(f" Rendering video for {platform}...")

    # Find ffmpeg executable
    ffmpeg = find_ffmpeg()

    if not AUDIO.exists():
        raise FileNotFoundError(f"Audio not found: {AUDIO}")
    if not ASS_FILE.exists():
        raise FileNotFoundError(f"Captions not found: {ASS_FILE}")

    # Get list of images
    images = sorted(IMG_DIR.glob("img_*.jpg"))
    if not images:
        raise FileNotFoundError(f"No images found in {IMG_DIR}")

    print(f" Found {len(images)} images")

    # Get audio duration
    audio_duration = get_audio_duration(AUDIO)
    duration_per_image = audio_duration / len(images)
    
    print(f" Audio duration: {audio_duration:.2f}s")
    print(f"  Each image will show for {duration_per_image:.2f}s")

    # Change to output directory so ffmpeg can find relative files
    import os
    os.chdir(OUTPUT_DIR)

    # Load settings from config (check for job-specific config first)
    import yaml
    job_config_path = OUTPUT_DIR / "settings.yaml"
    if job_config_path.exists():
        config_path = job_config_path
    else:
        config_path = BASE_DIR / "config" / "settings.yaml"
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    # Get platform specs
    platform_specs = config.get("platforms", {}).get(platform, {
        "width": 1080,
        "height": 1920
    })
    width = platform_specs.get("width", 1080)
    height = platform_specs.get("height", 1920)
    
    print(f" Platform: {platform} ({width}x{height})")
    
    transition_enabled = config.get("video", {}).get("transition", {}).get("enabled", True)
    transition_type = config.get("video", {}).get("transition", {}).get("type", "fade")
    transition_duration = config.get("video", {}).get("transition", {}).get("duration", 0.5)
    caption_style = config.get("video", {}).get("caption_style", "bounce")
    
    # Check if Ken Burns effect is enabled
    use_ken_burns = transition_type == "kenburns"
    
    # Create a filter that displays each image
    filter_parts = []
    zoompan_frames = int(duration_per_image * 30)
    for i, img in enumerate(images):
        if use_ken_burns:
            # Ken Burns zoom/pan effect
            filter_parts.append(
                f"[{i}:v]loop=loop=-1:size=1:start=0,"
                f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black,setsar=1,"
                f"zoompan=z='min(zoom+0.0015,1.4)':d={zoompan_frames}:fps=30:"
                f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={width}x{height},"
                f"trim=duration={duration_per_image},setpts=PTS-STARTPTS[v{i}]"
            )
        else:
            # Static image (no zoom/pan)
            filter_parts.append(
                f"[{i}:v]loop=loop=-1:size=1:start=0,"
                f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black,setsar=1,"
                f"trim=duration={duration_per_image},setpts=PTS-STARTPTS[v{i}]"
            )
    
    # Apply transitions between images using xfade (skip if kenburns since it's not an xfade transition)
    if transition_enabled and len(images) > 1 and not use_ken_burns:
        # Start with first video segment
        transition_filters = []
        
        # Chain xfade transitions between consecutive clips
        for i in range(len(images) - 1):
            if i == 0:
                # First transition: v0 + v1 -> t0
                transition_filters.append(
                    f"[v{i}][v{i+1}]xfade=transition={transition_type}:"
                    f"duration={transition_duration}:offset={duration_per_image - transition_duration}[t{i}]"
                )
            else:
                # Subsequent transitions: t(i-1) + v(i+1) -> t(i)
                transition_filters.append(
                    f"[t{i-1}][v{i+1}]xfade=transition={transition_type}:"
                    f"duration={transition_duration}:offset={(i+1)*duration_per_image - i*transition_duration - transition_duration}[t{i}]"
                )
        
        # Final output is the last transition
        final_video_tag = f"[t{len(images)-2}]"
        
        # Add ASS overlay only if captions enabled
        if caption_style != "none" and ASS_FILE.exists():
            ass_filter = f"{final_video_tag}ass=captions.ass[v]"
            full_filter = ';'.join(filter_parts + transition_filters + [ass_filter])
        else:
            # No captions - use video output directly
            full_filter = ';'.join(filter_parts + transition_filters)
            full_filter += f";{final_video_tag}copy[v]"
    else:
        # No transitions - use simple concatenation
        concat_inputs = ''.join(f"[v{i}]" for i in range(len(images)))
        concat_filter = f"{concat_inputs}concat=n={len(images)}:v=1:a=0[video]"
        
        # Add ASS overlay only if captions enabled
        if caption_style != "none" and ASS_FILE.exists():
            ass_filter = "[video]ass=captions.ass[v]"
            full_filter = ';'.join(filter_parts + [concat_filter, ass_filter])
        else:
            # No captions - use video output directly
            full_filter = ';'.join(filter_parts + [concat_filter])
            full_filter += ";[video]copy[v]"

    # Build ffmpeg command with multiple image inputs (no -loop here; loop handled in filter)
    cmd = [ffmpeg, "-y", "-nostdin"]  # -nostdin prevents keyboard input interference

    # Add all images as inputs (plain inputs; zoompan/filter does the looping)
    for img in images:
        cmd.extend(["-i", str(img.absolute())])
    
    # Add audio input
    cmd.extend(["-i", "voice.wav"])
    
    # Add filters and output options
    cmd.extend([
        "-filter_complex", full_filter,
        "-map", "[v]",
        "-map", f"{len(images)}:a",  # audio is the last input
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-t", str(audio_duration),  # Force video to match audio duration
        "final.mp4"
    ])

    subprocess.run(cmd, check=True)

    print(f" Final TikTok video created with {len(images)} image slideshow")


if __name__ == "__main__":
    main()





