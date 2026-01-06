import subprocess
import sys
import argparse
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
    # ---- STEP 1: parse args (topic optional) ----
    parser = argparse.ArgumentParser(description="Run pipeline")
    parser.add_argument("topic", nargs="?", help="Topic to generate content for")
    parser.add_argument("--use-stored-images", dest="use_stored_images", action="store_true",
                        help="Use existing images in images/ and skip make_images.py")
    args = parser.parse_args()

    if args.topic:
        topic = args.topic
    else:
        # Use fixed topic requested by user
        topic = "Things I Ignored Because She Was Cute"
        print(f"\n🎯 Using fixed topic: {topic}\n")

    print(f"\n🧠 TOPIC: {topic}")

    # ---- STEP 2: generate script ----
    # adjust filename if yours differs
    run("make_script.py", [topic])

    # ---- STEP 3: generate voice ----
    run("make_voice.py")

    # ---- STEP 4: generate one-word bouncing captions ----
    run("make_captions_bounce.py")
    
    # --- Step 5: make the video images (skip if using stored images) ----
    if not getattr(args, "use_stored_images", False):
        run("make_images.py")
    else:
        print("\nℹ️  Skipping image generation; using stored images in images/\n")

    # ---- STEP 6: render final video ----
    run("make_video_render.py")

    print("\n✅ PIPELINE COMPLETE")
    print("📁 Check: output/final.mp4")

if __name__ == "__main__":
    main()
