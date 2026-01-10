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

    # Get list of images (support jpg, jpeg, png)
    images = sorted(IMG_DIR.glob("img_*.[jp][pn][g]*"))
    if not images:
        raise FileNotFoundError(f"No images found in {IMG_DIR}")

    print(f" Found {len(images)} images")

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
    
    duration_per_image = target_duration / len(images)
    print(f"  Each image will show for {duration_per_image:.2f}s")
    
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
    
    # Get logo overlay settings
    logo_enabled = config.get("branding", {}).get("logo", {}).get("enabled", False)
    logo_path = config.get("branding", {}).get("logo", {}).get("image_path", "")
    logo_position = config.get("branding", {}).get("logo", {}).get("position", "top_right")
    logo_width = config.get("branding", {}).get("logo", {}).get("width", 300)
    logo_padding_x = config.get("branding", {}).get("logo", {}).get("padding_x", 30)
    logo_padding_y = config.get("branding", {}).get("logo", {}).get("padding_y", 30)
    
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
        
        # Build overlay chain: video -> captions -> logo
        filter_chain = []
        current_tag = final_video_tag
        
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
            full_filter = ';'.join(filter_parts + transition_filters + filter_chain)
            full_filter += f";{current_tag}copy[v]"
        else:
            # No captions or logo
            full_filter = ';'.join(filter_parts + transition_filters)
            full_filter += f";{final_video_tag}copy[v]"
    else:
        # No transitions - use simple concatenation
        concat_inputs = ''.join(f"[v{i}]" for i in range(len(images)))
        concat_filter = f"{concat_inputs}concat=n={len(images)}:v=1:a=0[video]"
        
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
            full_filter += ";[video]copy[v]"

    # Build ffmpeg command with multiple image inputs (no -loop here; loop handled in filter)
    cmd = [ffmpeg, "-y", "-nostdin"]  # -nostdin prevents keyboard input interference

    # Add all images as inputs (plain inputs; zoompan/filter does the looping)
    for img in images:
        cmd.extend(["-i", str(img.absolute())])
    
    # Add audio input if it exists
    if AUDIO.exists():
        cmd.extend(["-i", "voice.wav"])
        audio_index = len(images)
    else:
        audio_index = None
    
    # Add filters and output options
    cmd.extend([
        "-filter_complex", full_filter,
        "-map", "[v]",
    ])
    
    if audio_index is not None:
        cmd.extend(["-map", f"{audio_index}:a"])  # audio is the last input
    
    cmd.extend([
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
    ])
    
    if audio_index is not None:
        cmd.extend(["-c:a", "aac", "-b:a", "128k"])
    
    cmd.extend([
        "-t", str(target_duration),  # Force video to match target duration
        "temp_video.mp4"
    ])

    subprocess.run(cmd, check=True)

    # Check if end card is enabled
    end_card_enabled = config.get("branding", {}).get("end_card", {}).get("enabled", True)
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
        subprocess.run(end_card_cmd, check=True)
        
        # Concatenate main video with end card
        # Create concat list file
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
        subprocess.run(concat_cmd, check=True)
        
        # Cleanup temporary files
        Path("temp_video.mp4").unlink(missing_ok=True)
        Path("temp_endcard.mp4").unlink(missing_ok=True)
        Path("concat_list.txt").unlink(missing_ok=True)
        
        print(f" Final video created with end card")
    else:
        # No end card - just rename temp file to final (replace if exists)
        temp_file = Path("temp_video.mp4")
        final_file = Path("final.mp4")
        if final_file.exists():
            final_file.unlink()
        temp_file.rename(final_file)
        print(f" Final TikTok video created with {len(images)} image slideshow")


if __name__ == "__main__":
    main()





