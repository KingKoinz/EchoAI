"""
Complete TikTok Video Pipeline with Combo Renderer (Videos + Images)
One-click solution: Script → Voice → Captions → Videos + Images → Combo Render
"""
import subprocess
import sys
from pathlib import Path
import time
import os

BASE_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = BASE_DIR / "scripts"

# Add ffmpeg to PATH for Whisper
FFMPEG_BIN = r"C:\Users\Walt\Downloads\ffmpeg\ffmpeg-master-latest-win64-gpl\bin"
if Path(FFMPEG_BIN).exists():
    os.environ["PATH"] = FFMPEG_BIN + os.pathsep + os.environ.get("PATH", "")

def run_step(script_name, description):
    """Run a pipeline step and report status"""
    print(f"\n{'='*60}")
    print(f"🚀 STEP: {description}")
    print(f"{'='*60}")
    
    # Split script name and arguments
    parts = script_name.split(None, 1)
    script_file = parts[0]
    args = parts[1] if len(parts) > 1 else ""
    
    script_path = SCRIPTS_DIR / script_file
    if not script_path.exists():
        print(f"❌ Script not found: {script_path}")
        return False
    
    try:
        cmd = [sys.executable, str(script_path)]
        if args:
            # Remove quotes if present and add as single argument
            cmd.append(args.strip('"'))
        
        result = subprocess.run(
            cmd,
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
    """Run complete combo video pipeline"""
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║  TikTok Combo Video Pipeline - Complete Automation      ║
    ╚══════════════════════════════════════════════════════════╝
    
    This will:
    1. Generate AI script (Claude API)
    2. Generate voice audio (Eleven Labs API)
    3. Create styled captions
    4. Download video clips (Vecteezy/Pexels API)
    5. Download still images (Vecteezy/Pexels API)
    6. Render final combo video (videos + images with Ken Burns)
    
    ⚠️  WARNING: This uses API credits!
    - Claude API: ~$0.01-0.05 per run
    - Eleven Labs: Character quota
    - Vecteezy: Dynamic downloads based on script length
      * Short (30s): ~4 media files
      * Medium (50s): ~5-6 media files
      * Long (90s): ~10 media files
    
    """)
    
    # Confirm to proceed
    response = input("Continue? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("❌ Pipeline cancelled by user")
        return
    
    start_time = time.time()
    
    # Read topic from input/topics.txt
    topics_file = BASE_DIR / "input" / "topics.txt"
    if not topics_file.exists():
        print("❌ input/topics.txt not found!")
        return
    
    topic = topics_file.read_text().strip()
    if not topic:
        print("❌ input/topics.txt is empty!")
        return
    
    print(f"\n📝 Topic: {topic}\n")
    
    # Pipeline steps
    steps = [
        (f'make_script.py "{topic}"', "Generate AI Script"),
        ("make_voice.py", "Generate Voice Audio"),
        ("make_captions.py", "Create Styled Captions"),
        ("make_videos_vecteezy.py", "Download Video Clips"),
        ("make_images.py", "Download Still Images"),
        ("make_video_render_combo.py", "Render Combo Video (Videos + Images)"),
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
       - Images: images/img_01.jpg through img_N.jpg
       - Final Video: output/final.mp4 ✨
    
    🎬 Your combo TikTok video is ready to upload!
       (Dynamic mix of videos + Ken Burns images)
    
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
