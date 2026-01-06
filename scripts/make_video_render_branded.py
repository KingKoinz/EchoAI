"""
Render TikTok video with branded overlay layers (logo + lower third).

This script applies a logo overlay and a configurable lower-third banner
to an existing `output/final.mp4`. It is intentionally small and robust 
it does not attempt to remux or recreate the base slideshow/clip file.
"""
import subprocess
from pathlib import Path
import yaml
import sys
import shutil

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"
CONFIG_PATH = BASE_DIR / "config" / "settings.yaml"


def find_ffmpeg():
    candidates = [
        "ffmpeg",
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
    ]
    for c in candidates:
        if shutil.which(c):
            return c
    print("ffmpeg not found: add it to PATH or install from https://ffmpeg.org/")
    sys.exit(1)


def load_config():
    if not CONFIG_PATH.exists():
        return {}
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def render_branded_video(input_file=None, output_file=None):
    """Apply logo overlay and lower-third to an existing video file.

    - `input_file` defaults to `output/final.mp4`.
    - `output_file` defaults to overwrite `output/final.mp4` (creates a temp file).
    """
    cfg = load_config()
    branding = cfg.get("branding", {})

    logo_cfg = branding.get("logo", {})
    lt_cfg = branding.get("lower_third", {})
    text_cfg = branding.get("text", {})

    logo_enabled = logo_cfg.get("enabled", True)
    logo_path = BASE_DIR / logo_cfg.get("image_path", "echo_transparent.png")
    logo_width = logo_cfg.get("width", 200)
    logo_pos = logo_cfg.get("position", "top_right")
    logo_pad_x = logo_cfg.get("padding_x", 30)
    logo_pad_y = logo_cfg.get("padding_y", 30)

    lt_enabled = lt_cfg.get("enabled", True)
    lt_height = lt_cfg.get("height", 90)
    lt_y = lt_cfg.get("y_position", 1700)
    lt_bg = lt_cfg.get("bg_color", "0x000000")
    lt_opacity = lt_cfg.get("bg_opacity", 0.85)
    lt_accent = lt_cfg.get("accent_color", "0xCC0000")
    lt_accent_h = lt_cfg.get("accent_height", 8)

    channel_name = branding.get("channel_name", "Channel")
    font_size = text_cfg.get("size", 48)
    font_color = text_cfg.get("color", "white")
    font_file = text_cfg.get("fontfile", r"C:\Windows\Fonts\impact.ttf")

    if input_file is None:
        input_file = OUTPUT_DIR / "final.mp4"
    if output_file is None:
        output_tmp = OUTPUT_DIR / "final_branded_tmp.mp4"
    else:
        output_tmp = Path(output_file)

    if not Path(input_file).exists():
        print(f"Input video not found: {input_file}")
        return False

    ffmpeg = find_ffmpeg()

    inputs = [str(input_file)]
    if logo_enabled and logo_path.exists():
        inputs.append(str(logo_path))

    # Start building filter_complex
    filter_parts = []
    last = "[0:v]"

    # If logo present, scale and overlay it
    if logo_enabled and logo_path.exists():
        # logo is input 1
        filter_parts.append(f"[1:v]scale={logo_width}:-1[logo]")
        # Use explicit ffmpeg variables for overlay positioning to avoid
        # runtime differences between ffmpeg builds (use main_w/main_h and
        # overlay_w/overlay_h which are widely supported).
        if logo_pos == "top_right":
            ox = f"main_w-overlay_w-{logo_pad_x}"
            oy = f"{logo_pad_y}"
        elif logo_pos == "top_left":
            ox = f"{logo_pad_x}"
            oy = f"{logo_pad_y}"
        elif logo_pos == "bottom_right":
            ox = f"main_w-overlay_w-{logo_pad_x}"
            oy = f"main_h-overlay_h-{logo_pad_y}"
        else:
            ox = f"{logo_pad_x}"
            oy = f"main_h-overlay_h-{logo_pad_y}"
        filter_parts.append(f"{last}[logo]overlay={ox}:{oy}[vlogo]")
        last = "[vlogo]"

    # Lower third
    if lt_enabled:
        # draw background box
        filter_parts.append(
            f"{last}drawbox=x=0:y={lt_y}:w=1080:h={lt_height}:color={lt_bg}@{lt_opacity}:t=fill[with_lt]"
        )
        # accent bar
        filter_parts.append(
            f"[with_lt]drawbox=x=0:y={lt_y}:w=1080:h={lt_accent_h}:color={lt_accent}:t=fill[with_accent]"
        )
        # draw text
        chan_escaped = channel_name.replace(":", "\\:").replace("'", "\\'")
        # Use fontfile if available
        drawtext = (
            f"[with_accent]drawtext=text='{chan_escaped}':fontfile={font_file}:fontsize={font_size}:"
            f"fontcolor={font_color}:x=(w-text_w)/2:y={lt_y + (lt_height//2) - (font_size//2)}:borderw=3:bordercolor=black[out]"
        )
        filter_parts.append(drawtext)
        last = "[out]"

    # Assemble filter_complex
    filter_complex = ";".join(filter_parts) if filter_parts else None

    # Ensure final output label is [out] so we can map it later
    if filter_complex and not filter_complex.strip().endswith("[out]"):
        # Determine last label (e.g. [vlogo] or [with_lt]) and map to [out]
        # We'll append a null filter to rename it to [out]
        # Find last bracketed label
        import re
        labels = re.findall(r"\[[^\]]+\]", filter_complex)
        if labels:
            last_label = labels[-1]
            filter_complex = filter_complex + ";" + last_label + "null[out]"

    cmd = [ffmpeg, "-y"]
    for inp in inputs:
        cmd.extend(["-i", inp])

    if filter_complex:
        cmd.extend(["-filter_complex", filter_complex, "-map", "[out]", "-map", "0:a?"])
    else:
        # no video filters to apply, just copy
        cmd.extend(["-map", "0:v", "-map", "0:a?"])

    cmd.extend(["-c:v", "libx264", "-preset", "medium", "-crf", "23", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-shortest", str(output_tmp)])

    try:
        print("Running ffmpeg overlay command...")
        subprocess.run(cmd, check=True)
        # Replace original file if possible; otherwise write a branded copy
        final_path = OUTPUT_DIR / "final.mp4"
        try:
            if output_tmp.exists():
                output_tmp.replace(final_path)
            print(f" Branded video saved to {final_path}")
        except PermissionError:
            # Could not replace (file locked). Save as a separate branded file.
            fallback = OUTPUT_DIR / "final_branded.mp4"
            try:
                if output_tmp.exists():
                    # prefer atomic move when possible
                    output_tmp.replace(fallback)
                print(f" Branded video saved to {fallback} (could not replace final.mp4)")
            except Exception:
                import shutil as _sh
                _sh.move(str(output_tmp), str(fallback))
                print(f" Branded video moved to {fallback} (could not replace final.mp4)")

        return True
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg failed: {e}")
        return False


def main():
    render_branded_video()


if __name__ == "__main__":
    main()
