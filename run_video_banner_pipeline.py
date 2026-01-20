"""
Complete TikTok Video Pipeline with Branded Overlays
One-click solution: Script → Voice → Captions → Videos → Branded Render
"""
import subprocess
import sys
from pathlib import Path
import time
import yaml

BASE_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = BASE_DIR / "scripts"

def load_config():
    """Load configuration from settings.yaml"""
    config_path = BASE_DIR / "config" / "settings.yaml"
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def get_caption_script(config):
    """Get the appropriate caption script based on config"""
    caption_style = config.get('video', {}).get('caption_style', 'bounce')
    
    style_map = {
        'bounce': 'make_captions_bounce.py',
        'color_box': 'make_captions_color_box.py',
        'karaoke': 'make_captions_karaoke.py',
        'yellow_box': 'make_captions.py',  # default yellow_box
        'white_box': 'make_captions.py',   # fallback to default
        'single_pop': 'make_captions.py',  # fallback to default
        'none': None
    }
    
    return style_map.get(caption_style, 'make_captions_bounce.py')
    """Run a pipeline step and report status"""
    print(f"\n{'='*60}")
    print(f"🚀 STEP: {description}")
    print(f"{'='*60}")
    
    script_path = SCRIPTS_DIR / script_name
    if not script_path.exists():
        print(f"❌ Script not found: {script_path}")
        return False
    
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            check=True,
            capture_output=False,
            text=True
        )
        print(f"✅ {description} - COMPLETED")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - FAILED")
        print(f"Error: {e}")
        return False

def main():
    """Run complete branded video pipeline"""
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║  TikTok Branded Video Pipeline - Complete Automation    ║
    ╚══════════════════════════════════════════════════════════╝
    
    This will:
    1. Generate AI script (Claude API)
    2. Generate voice audio (Eleven Labs API)
    3. Create styled captions
    4. Download video clips (Vecteezy/Pexels API)
    5. Render final branded video with overlays
    
    ⚠️  WARNING: This uses API credits!
    - Claude API: ~$0.01-0.05 per run
    - Eleven Labs: Character quota
    - Vecteezy: 1 download per video = 5-10 quota
    
    """)
    
    # Confirm to proceed
    response = input("Continue? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("[CANCELLED] Pipeline cancelled by user")
        return
    
    start_time = time.time()
    
    # Load configuration
    config = load_config()
    
    # Get platform from config
    platform = config.get("video", {}).get("platform", "tiktok")
    
    # Get caption script based on config
    caption_script = get_caption_script(config)
    
    # Pipeline steps
    steps = [
        ("make_script.py", "Generate AI Script"),
        ("make_voice.py", "Generate Voice Audio"),
        (f"make_video_hook.py {platform}", "Render Hook Segment"),
    ]
    
    # Add caption step if not none
    if caption_script:
        steps.append((caption_script, f"Create Styled Captions ({config.get('video', {}).get('caption_style', 'bounce')})"))
    else:
        print("⚠️  Caption generation disabled (caption_style: none)")
    
    steps.extend([
        ("make_images.py", "Generate Images"),
        ("make_video_render.py", "Render Body Video (image slideshow)"),
        (f"make_video_concat.py {platform}", "Concatenate Hook + Body + Endcard"),
    ])
    
    # Execute pipeline
    for script, description in steps:
        success = run_step(script, description)
        if not success:
            print(f"\n❌ Pipeline FAILED at: {description}")
            print("Fix the error and try again.")
            return
        time.sleep(1)  # Brief pause between steps
    
    # Success!
    elapsed = time.time() - start_time
    print(f"""
    
    ╔══════════════════════════════════════════════════════════╗
    ║  🎉 PIPELINE COMPLETED SUCCESSFULLY! 🎉                  ║
    ╚══════════════════════════════════════════════════════════╝
    
    ⏱️  Total time: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)
    
    📁 Output files:
       - Script: output/script.txt
       - Audio: output/voice.wav
       - Captions: output/captions.srt, output/captions.ass
       - Videos: videos/video_01.mp4 through video_N.mp4
       - Final Video: output/final.mp4 ✨
    
    📺 Your branded TikTok video is ready to upload!
    
    Next steps:
    1. Review output/final.mp4
    2. Upload to TikTok
    3. Add hashtags and description
    4. Monitor performance
    
    """)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[CANCELLED] Pipeline interrupted by user (Ctrl+C)")
    except Exception as e:
        print(f"\n\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
