"""
Render TikTok video with professional blue gradient overlays + logo
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

def render_branded_video(use_images=False):
    """Render video with blue gradient bars + logo overlay"""
    config = load_config()
    branding = config.get("branding", {})
    
    # Settings
    logo_image = branding.get("logo_image", "echo_transparent.png")
    logo_width = branding.get("logo_width", 200)
    logo_padding = branding.get("logo_padding", 15)
    
    top_bar = branding.get("top_bar", {})
    top_height = top_bar.get("height", 180)  # Much thicker for impact
    top_color = top_bar.get("gradient_start", "0x0033AA")
    top_opacity = top_bar.get("opacity", 0.85)
    
    bottom_bar = branding.get("bottom_bar", {})
    bottom_height = bottom_bar.get("height", 150)  # Much thicker for impact
    bottom_color = bottom_bar.get("gradient_start", "0x001166")
    bottom_opacity = bottom_bar.get("opacity", 0.85)
    
    # Video dimensions (all videos are normalized to this)
    video_width = 1080
    video_height = 1920
    
    # Calculate bar sizes as percentage of video height
    top_height_percent = top_height / video_height
    bottom_height_percent = bottom_height / video_height
    
    # Paths
    logo_path = BASE_DIR / logo_image
    audio_file = OUTPUT_DIR / "voice.wav"
    captions_file = OUTPUT_DIR / "captions.ass"
    output_file = OUTPUT_DIR / "final.mp4"
    
    # Media files
    if use_images:
        media_dir = IMG_DIR
        media_files = sorted(media_dir.glob("img_*.jpg"))
        media_type = "images"
    else:
        media_dir = VIDEO_DIR
        media_files = sorted(media_dir.glob("video_*.mp4"))
        media_type = "video clips"
    
    if not media_files:
        print(f" No {media_type} found in {media_dir}")
        return False
    
    print(f" Rendering BRANDED video with {len(media_files)} {media_type}...")
    print(f" Style: Blue gradient bars + logo")
    
    # Build ffmpeg inputs
    inputs = []
    for media_file in media_files:
        inputs.extend(["-i", str(media_file)])
    inputs.extend(["-i", str(audio_file)])
    audio_index = len(media_files)
    
    # Build filter complex - normalize all videos first, then concat, then apply bars
    concat_filters = []
    
    for i in range(len(media_files)):
        # Normalize each video to standard size
        concat_filters.append(
            f"[{i}:v]scale={video_width}:{video_height}:"
            f"force_original_aspect_ratio=decrease,"
            f"pad={video_width}:{video_height}:(ow-iw)/2:(oh-ih)/2:black,"
            f"setsar=1,fps=30[v{i}];"
        )
    
    # Concatenate all normalized videos
    concat_input = "".join([f"[v{i}]" for i in range(len(media_files))])
    concat_filters.append(f"{concat_input}concat=n={len(media_files)}:v=1:a=0[base];")
    
    filter_complex = "".join(concat_filters)
    
    # RGB values for gradients
    top_start_r, top_start_g, top_start_b = 0x00, 0x33, 0xAA
    top_end_r, top_end_g, top_end_b = 0x00, 0x11, 0x66
    bottom_start_r, bottom_start_g, bottom_start_b = 0x00, 0x11, 0x66
    bottom_end_r, bottom_end_g, bottom_end_b = 0x00, 0x00, 0x33
    
    # Create high-quality gradient bars using geq filter (applied to concatenated video)
    filter_complex += (
        f"nullsrc=s={video_width}x{top_height}:d=60,geq="
        f"r='lerp({top_start_r},{top_end_r},Y/{top_height})':"
        f"g='lerp({top_start_g},{top_end_g},Y/{top_height})':"
        f"b='lerp({top_start_b},{top_end_b},Y/{top_height})':"
        f"a='255*{top_opacity}'[top_grad];"
    )
    
    bottom_y = video_height - bottom_height
    filter_complex += (
        f"nullsrc=s={video_width}x{bottom_height}:d=60,geq="
        f"r='lerp({bottom_start_r},{bottom_end_r},Y/{bottom_height})':"
        f"g='lerp({bottom_start_g},{bottom_end_g},Y/{bottom_height})':"
        f"b='lerp({bottom_start_b},{bottom_end_b},Y/{bottom_height})':"
        f"a='255*{bottom_opacity}'[bottom_grad];"
    )
    
    # Overlay gradient bars on the concatenated video
    filter_complex += f"[base][top_grad]overlay=0:0:shortest=1[with_top];"
    filter_complex += f"[with_top][bottom_grad]overlay=0:{bottom_y}:shortest=1[with_bars];"
    
    # Add logo overlay in top right (positioned dynamically based on video dimensions)
    logo_x = video_width - logo_width - logo_padding
    logo_y = logo_padding
    logo_path_str = str(logo_path).replace("\\", "\\\\\\\\").replace(":", "\\\\:")
    filter_complex += f"movie={logo_path_str},scale={logo_width}:-1[logo];"
    filter_complex += f"[with_bars][logo]overlay={logo_x}:{logo_y}[with_logo];"
    
    # Add captions (escape path properly for Windows)
    captions_str = str(captions_file).replace("\\", "\\\\\\\\").replace(":", "\\\\:")
    filter_complex += f"[with_logo]subtitles=filename={captions_str}[out]"
    
    # Save filter to file
    filter_file = BASE_DIR / "filter_complex.txt"
    filter_file.write_text(filter_complex, encoding="utf-8")
    
    # FFmpeg command
    ffmpeg = find_ffmpeg()
    cmd = [
        ffmpeg, "-y", "-nostdin",
        *inputs,
        "-filter_complex_script", str(filter_file),
        "-map", "[out]",
        "-map", f"{audio_index}:a",
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        str(output_file)
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print(f" Video created: {output_file}")
        print(f" Style: Blue gradient overlays + logo")
        filter_file.unlink()
        return True
    except subprocess.CalledProcessError as e:
        print(f" FFmpeg error: {e}")
        return False

def main():
    render_branded_video(use_images=False)

if __name__ == "__main__":
    main()
