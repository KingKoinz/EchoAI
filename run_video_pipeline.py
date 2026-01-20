import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SCRIPTS = BASE_DIR / "scripts"

def run(script_name, args=None):
    cmd = [sys.executable, str(SCRIPTS / script_name)]
    if args:
        cmd.extend(args)

    print(f"\n▶ Running: {script_name}")
    subprocess.run(cmd, check=True)

def main():
    # ---- STEP 1: get topic ----
    if len(sys.argv) > 1:
        topic = sys.argv[1]
    else:
        # Use the requested fixed topic instead of auto-generating
        topic = "Things I Ignored Because She Was Cute"
        print(f"\n[*] Using fixed topic: {topic}\n")


    print(f"\n[TOPIC] {topic}")

    # ---- STEP 2: generate script ----
    # adjust filename if yours differs
    run("make_script.py", [topic])

    # ---- STEP 3: generate voice ----
    run("make_voice.py")

    # Load caption style from config
    import yaml
    config_path = BASE_DIR / "config" / "settings.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # ---- STEP 3.5: render hook segment ----
    platform = config.get("video", {}).get("platform", "tiktok")
    run("make_video_hook.py", [platform])

    # ---- STEP 4: generate captions based on config ----
    
    caption_style = config.get("video", {}).get("caption_style", "color_box")
    
    if caption_style == "bounce":
        run("make_captions_bounce.py")
    elif caption_style == "color_box":
        run("make_captions_color_box.py")
    elif caption_style == "karaoke":
        run("make_captions_karaoke.py")
    elif caption_style == "yellow_box":
        run("make_captions_yellow_box.py")
    elif caption_style == "white_box":
        run("make_captions_white_box.py")
    elif caption_style == "single_pop":
        run("make_captions_single_pop.py")
    else:
        run("make_captions_color_box.py")  # Default

    # --- Step 5: generate topic-related images (used for slideshow) ----
    run("make_images.py")

    # ---- STEP 6: render body video using image slideshow with motion ----
    run("make_video_render.py")

    # ---- STEP 7: concatenate hook + body + endcard ----
    run("make_video_concat.py", [platform])

    print("\n[SUCCESS] VIDEO PIPELINE COMPLETE")
    print("[OUTPUT] Check: output/final.mp4")

if __name__ == "__main__":
    main()
