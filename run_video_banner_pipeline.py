"""
Complete TikTok Video Pipeline with Branded Overlays
One-click solution: Script → Voice → Captions → Videos → Branded Render
"""
import subprocess
import sys
from pathlib import Path
import time

BASE_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = BASE_DIR / "scripts"

def run_step(script_name, description):
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
        print("❌ Pipeline cancelled by user")
        return
    
    start_time = time.time()
    
    # Pipeline steps
    steps = [
        ("make_script.py", "Generate AI Script"),
        ("make_voice.py", "Generate Voice Audio"),
        ("make_captions_color_box.py", "Create Styled Captions (color-box)") ,
        ("make_images.py", "Generate Images"),
        ("make_video_render.py", "Render Video (image slideshow)"),
    ]
    
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
        print("\n\n❌ Pipeline interrupted by user (Ctrl+C)")
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
