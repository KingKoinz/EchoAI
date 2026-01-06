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
        print(f"\n🎯 Using fixed topic: {topic}\n")


    print(f"\n🧠 TOPIC: {topic}")

    # ---- STEP 2: generate script ----
    # adjust filename if yours differs
    run("make_script.py", [topic])

    # ---- STEP 3: generate voice ----
    run("make_voice.py")

    # ---- STEP 4: generate color-box captions ----
    run("make_captions_color_box.py")

    # --- Step 5: generate topic-related images (used for slideshow) ----
    run("make_images.py")

    # ---- STEP 6: render final video using image slideshow with motion ----
    run("make_video_render.py")

    print("\n✅ VIDEO PIPELINE COMPLETE")
    print("📁 Check: output/final.mp4")

if __name__ == "__main__":
    main()
