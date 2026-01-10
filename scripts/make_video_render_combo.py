"""
Render TikTok video mixing video clips and still images with logo overlay
"""
import subprocess
from pathlib import Path
import yaml
import sys
import shutil

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"
IMG_DIR = BASE_DIR / "images"
VIDEO_DIR = BASE_DIR / "videos"
CONFIG_PATH = BASE_DIR / "config" / "settings.yaml"

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

def render_combo_video(platform="tiktok"):
    """Render video mixing video clips and still images with logo overlay"""
    config = load_config()
    branding = config.get("branding", {})
    
    # Get platform specs
    platforms = config.get("platforms", {})
    platform_spec = platforms.get(platform, platforms.get("tiktok"))
    video_width = platform_spec.get("width", 1080)
    video_height = platform_spec.get("height", 1920)
    
    # Get caption style from config
    caption_style = config.get("video", {}).get("caption_style", "bounce")
    
    # Get logo overlay settings from config
    logo_enabled = config.get("branding", {}).get("logo", {}).get("enabled", False)
    logo_image = config.get("branding", {}).get("logo", {}).get("image_path", "images/echo_transparent.png")
    logo_position = config.get("branding", {}).get("logo", {}).get("position", "top_right")
    logo_width = config.get("branding", {}).get("logo", {}).get("width", 260)
    logo_padding = config.get("branding", {}).get("logo", {}).get("padding_x", 15)
    
    print(f" Platform: {platform} ({video_width}x{video_height})")
    
    # Paths
    logo_path = BASE_DIR / logo_image
    audio_file = OUTPUT_DIR / "voice.wav"
    captions_file = OUTPUT_DIR / "captions.ass"
    output_file = OUTPUT_DIR / "final.mp4"
    
    # Calculate number of segments based on audio length
    import subprocess as sp
    result = sp.run([find_ffmpeg(), "-i", str(audio_file)], 
                    capture_output=True, text=True)
    duration_line = [line for line in result.stderr.split('\n') if 'Duration:' in line]
    if duration_line:
        # Parse duration: "Duration: 00:00:53.16"
        duration_str = duration_line[0].split('Duration: ')[1].split(',')[0]
        h, m, s = duration_str.split(':')
        audio_duration = int(h) * 3600 + int(m) * 60 + float(s)
    else:
        audio_duration = 53.16  # Default fallback
    
    # Calculate number of segments (aim for 8-10 seconds per segment)
    target_segment_duration = 9.0
    total_segments = max(4, int(audio_duration / target_segment_duration))  # Minimum 4 segments
    
    # Get available media files
    available_videos = sorted(VIDEO_DIR.glob("video_*.mp4"))
    available_images = sorted(IMG_DIR.glob("img_*.jpg"))
    
    # Calculate actual total time we need to fill
    # First, check the actual video durations
    import subprocess as sp
    video_durations = []
    for vid in available_videos[:6]:  # Check up to 6 videos
        try:
            result = sp.run([find_ffmpeg(), "-i", str(vid)], 
                          capture_output=True, text=True)
            duration_line = [line for line in result.stderr.split('\n') if 'Duration:' in line]
            if duration_line:
                duration_str = duration_line[0].split('Duration: ')[1].split(',')[0]
                h, m, s = duration_str.split(':')
                vid_duration = int(h) * 3600 + int(m) * 60 + float(s)
                video_durations.append(vid_duration)
        except:
            pass
    
    # Adjust segment count based on actual video availability
    # If videos average less than target, we need more segments
    avg_video_duration = sum(video_durations) / len(video_durations) if video_durations else target_segment_duration
    segment_duration = target_segment_duration  # Images will be this long
    
    # Calculate how many segments we need to fill the audio duration
    # Pattern: V-I-V-I-V-I... alternate to fill audio_duration
    # Each video uses its natural length, each image uses segment_duration
    
    # Start with what we have available
    max_videos_to_use = min(len(available_videos), 25)  # Use all videos up to 25
    max_images_to_use = min(len(available_images), 30)  # Use all images up to 30
    
    # Calculate expected total time if we use all available media once
    expected_video_time = sum(video_durations[:max_videos_to_use]) if video_durations else (max_videos_to_use * avg_video_duration)
    expected_image_time = max_images_to_use * segment_duration
    expected_total = expected_video_time + expected_image_time
    
    # Determine how many media files we actually need
    if expected_total >= audio_duration:
        # We have enough content - just trim to fit
        ratio = audio_duration / expected_total
        num_videos = max(2, int(max_videos_to_use * ratio))
        num_images = max(2, int(max_images_to_use * ratio))
        video_files = available_videos[:num_videos]
        image_files = available_images[:num_images]
    else:
        # Not enough content - we'll need to loop/repeat media files
        print(f"   ⚠️ Only {expected_total:.1f}s of content for {audio_duration:.1f}s audio")
        print(f"   🔄 Will loop media files to fill duration")
        
        # Use all available media and calculate how many times to repeat
        base_video_files = list(available_videos[:max_videos_to_use])
        base_image_files = list(available_images[:max_images_to_use])
        
        # Calculate how many loops we need
        if expected_total > 0:
            loops_needed = int(audio_duration / expected_total) + 1
        else:
            loops_needed = 2
        
        # Repeat the media files to fill the duration
        video_files = base_video_files * loops_needed
        image_files = base_image_files * loops_needed
        
        # Trim to approximately match audio duration
        # Alternate V-I-V-I pattern and stop when we exceed audio duration
        estimated_time = 0
        final_video_files = []
        final_image_files = []
        v_idx = 0
        i_idx = 0
        
        while estimated_time < audio_duration and (v_idx < len(video_files) or i_idx < len(image_files)):
            # Add video
            if v_idx < len(video_files):
                final_video_files.append(video_files[v_idx])
                vid_dur = video_durations[v_idx % len(video_durations)] if video_durations else avg_video_duration
                estimated_time += vid_dur
                v_idx += 1
            
            if estimated_time >= audio_duration:
                break
                
            # Add image
            if i_idx < len(image_files):
                final_image_files.append(image_files[i_idx])
                estimated_time += segment_duration
                i_idx += 1
        
        video_files = final_video_files
        image_files = final_image_files
        num_videos = len(video_files)
        num_images = len(image_files)
    
    if not video_files and not image_files:
        print(f" No videos or images found")
        return False
    
    total_segments = num_videos + num_images
    print(f" Rendering COMBO video:")
    print(f"     Audio: {audio_duration:.1f}s  {total_segments} segments")
    print(f"    {len(video_files)} video clips (natural length)")
    print(f"     {len(image_files)} still images (~{segment_duration:.1f}s each)")
    print(f"    Logo overlay (no gradient bars)")
    
    # Build ffmpeg inputs - alternate between videos and images
    inputs = []
    all_media = []
    
    # Alternate: video, image, video, image, video, image
    for i in range(max(len(video_files), len(image_files))):
        if i < len(video_files):
            inputs.extend(["-i", str(video_files[i])])
            all_media.append(("video", len(all_media)))
        
        if i < len(image_files):
            # Just add image input (no -loop flag, we'll handle it in filter)
            inputs.extend(["-i", str(image_files[i])])
            all_media.append(("image", len(all_media)))
    
    # Add audio
    inputs.extend(["-i", str(audio_file)])
    audio_index = len(all_media)  # Audio is after all media files
    
    # Build filter complex
    filter_parts = []
    
    # Process each media file (normalize and prepare)
    # Calculate zoompan duration in frames (segment_duration * fps)
    zoompan_frames = int(segment_duration * 30)
    
    for idx, (media_type, _) in enumerate(all_media):
        if media_type == "image":
            # Convert image to video with Ken Burns zoom effect
            # Use loop filter to repeat the image, then zoompan for Ken Burns effect
            # Add trim and setpts to ensure proper timing for concat
            filter_parts.append(
                f"[{idx}:v]loop=loop=-1:size=1:start=0,"
                f"scale={video_width}:{video_height}:"
                f"force_original_aspect_ratio=decrease,"
                f"pad={video_width}:{video_height}:(ow-iw)/2:(oh-ih)/2:black,"
                f"setsar=1,"
                f"zoompan=z='min(zoom+0.0015,1.5)':d={zoompan_frames}:fps=30:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={video_width}x{video_height},"
                f"trim=duration={segment_duration},setpts=PTS-STARTPTS[v{idx}];"
            )
        else:
            # Process video - use natural duration, just normalize format for concat
            filter_parts.append(
                f"[{idx}:v]scale={video_width}:{video_height}:"
                f"force_original_aspect_ratio=decrease,"
                f"pad={video_width}:{video_height}:(ow-iw)/2:(oh-ih)/2:black,"
                f"setsar=1,fps=30,setpts=PTS-STARTPTS[v{idx}];"
            )
    
    # Concatenate all media clips
    concat_input = "".join([f"[v{i}]" for i in range(len(all_media))])
    filter_parts.append(f"{concat_input}concat=n={len(all_media)}:v=1:a=0[base];")
    
    filter_complex = "".join(filter_parts)
    
    # Add logo overlay if enabled
    if logo_enabled:
        # Calculate logo position
        if logo_position == "top_right":
            logo_x = video_width - logo_width - logo_padding
            logo_y = logo_padding
        elif logo_position == "top_left":
            logo_x = logo_padding
            logo_y = logo_padding
        elif logo_position == "bottom_right":
            logo_x = video_width - logo_width - logo_padding
            logo_y = video_height - logo_width - logo_padding  # Approximate square logo
        elif logo_position == "bottom_left":
            logo_x = logo_padding
            logo_y = video_height - logo_width - logo_padding
        else:  # default top_right
            logo_x = video_width - logo_width - logo_padding
            logo_y = logo_padding
        
        logo_path_str = str(logo_path).replace("\\", "\\\\\\\\").replace(":", "\\\\:")
        filter_complex += f"movie={logo_path_str},scale={logo_width}:-1,loop=loop=-1:size=1[logo];"
        filter_complex += f"[base][logo]overlay={logo_x}:{logo_y}[with_logo];"
        base_tag = "[with_logo]"
    else:
        base_tag = "[base]"
    
    # Add captions
    captions_str = str(captions_file).replace("\\", "\\\\\\\\").replace(":", "\\\\:")
    filter_complex += f"{base_tag}subtitles=filename={captions_str}[out]"
    
    # Save filter to file
    filter_file = BASE_DIR / "filter_complex.txt"
    filter_file.write_text(filter_complex, encoding="utf-8")
    
    # FFmpeg command
    ffmpeg = find_ffmpeg()
    temp_output = BASE_DIR / "output" / "temp_video.mp4"
    cmd = [
        ffmpeg, "-y", "-nostdin",
        *inputs,
        "-filter_complex_script", str(filter_file),
        "-map", "[out]",
        "-map", f"{audio_index}:a",
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",  # Stop when shortest stream (audio) ends
        str(temp_output)
    ]
    
    try:
        subprocess.run(cmd, check=True)
        filter_file.unlink()
        
        # Check if end card is enabled
        config = load_config()
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
                "-vf", f"scale={video_width}:{video_height}:force_original_aspect_ratio=decrease,pad={video_width}:{video_height}:(ow-iw)/2:(oh-ih)/2:black",
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "23",
                "-pix_fmt", "yuv420p",
                str(BASE_DIR / "output" / "temp_endcard.mp4")
            ]
            subprocess.run(end_card_cmd, check=True)
            
            # Concatenate main video with end card
            concat_list = BASE_DIR / "output" / "concat_list.txt"
            with open(concat_list, "w") as f:
                f.write(f"file 'temp_video.mp4'\n")
                f.write(f"file 'temp_endcard.mp4'\n")
            
            concat_cmd = [
                ffmpeg, "-y", "-nostdin",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_list),
                "-c", "copy",
                str(output_file)
            ]
            subprocess.run(concat_cmd, check=True)
            
            # Cleanup temporary files
            temp_output.unlink(missing_ok=True)
            (BASE_DIR / "output" / "temp_endcard.mp4").unlink(missing_ok=True)
            concat_list.unlink(missing_ok=True)
            
            print(f" Combo video created with end card: {output_file}")
        else:
            # No end card - just rename temp file to final (replace if exists)
            if output_file.exists():
                output_file.unlink()
            temp_output.rename(output_file)
            print(f" Combo video created: {output_file}")
        
        print(f"    Videos +  Images +  Logo +  Captions")
        return True
    except subprocess.CalledProcessError as e:
        print(f" FFmpeg error: {e}")
        return False

def main():
    # Get platform from command line argument
    platform = sys.argv[1] if len(sys.argv) > 1 else "tiktok"
    render_combo_video(platform)

if __name__ == "__main__":
    main()
