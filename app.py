"""
EchoAI Web Application - Flask Backend
"""
from flask import Flask, render_template, request, jsonify, send_file, session, send_from_directory
from flask_cors import CORS
from pathlib import Path
import uuid
import subprocess
import sys
import json
import yaml
from datetime import datetime
import threading
import os
import shutil

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB total request limit
CORS(app)

BASE_DIR = Path(__file__).resolve().parent
JOBS_DIR = BASE_DIR / "jobs"
JOBS_DIR.mkdir(exist_ok=True)

SHOWCASE_DIR = BASE_DIR / "static" / "showcase"
SHOWCASE_DIR.mkdir(exist_ok=True)
SHOWCASE_TRACKER = BASE_DIR / "config" / "showcase.json"

# Job status tracker
JOBS = {}

def load_showcase():
    if SHOWCASE_TRACKER.exists():
        with open(SHOWCASE_TRACKER, "r") as f:
            return json.load(f)
    return []

def save_showcase(data):
    with open(SHOWCASE_TRACKER, "w") as f:
        json.dump(data, f, indent=2)

def add_to_showcase(video_path, job_id):
    """Add video to showcase and cleanup old ones"""
    showcase = load_showcase()
    
    # Copy video to showcase directory
    showcase_video = SHOWCASE_DIR / f"user_{job_id}.mp4"
    shutil.copy(video_path, showcase_video)
    
    # Add to tracker
    showcase.append({
        "id": job_id,
        "filename": f"user_{job_id}.mp4",
        "created_at": datetime.now().isoformat(),
        "views": 0
    })
    
    # Keep only most recent 20 videos
    if len(showcase) > 20:
        # Remove oldest videos
        to_remove = showcase[:-20]
        showcase = showcase[-20:]
        
        for video in to_remove:
            old_file = SHOWCASE_DIR / video["filename"]
            if old_file.exists():
                old_file.unlink()
    
    save_showcase(showcase)

def cleanup_old_showcase_videos():
    """Remove videos older than 7 days"""
    showcase = load_showcase()
    now = datetime.now()
    updated_showcase = []
    
    for video in showcase:
        created = datetime.fromisoformat(video["created_at"])
        age_days = (now - created).days
        
        if age_days < 7:
            updated_showcase.append(video)
        else:
            # Delete old video
            old_file = SHOWCASE_DIR / video["filename"]
            if old_file.exists():
                old_file.unlink()
    
    if len(updated_showcase) != len(showcase):
        save_showcase(updated_showcase)

# Job status tracker

def load_config():
    """Load settings from YAML"""
    config_path = BASE_DIR / "config" / "settings.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def run_pipeline_async(job_id, topic, platform, style, voice, duration, transition, caption_style, content_type, logo_option):
    """Run video generation pipeline in background"""
    try:
        JOBS[job_id]["status"] = "processing"
        JOBS[job_id]["stage"] = "Generating script..."
        
        job_dir = JOBS_DIR / job_id
        job_dir.mkdir(exist_ok=True)
        
        # Update config for this job
        config = load_config()
        config["video"]["duration_seconds"] = duration
        config["video"]["style"] = style
        config["video"]["voice"] = voice
        config["video"]["transition"]["type"] = transition
        config["video"]["caption_style"] = caption_style
        
        # Update branding config
        if logo_option == "default":
            config["branding"]["logo"]["enabled"] = True
        elif logo_option == "upload" and JOBS[job_id].get("logo_path"):
            config["branding"]["logo"]["enabled"] = True
            config["branding"]["logo"]["image_path"] = JOBS[job_id]["logo_path"]
        elif logo_option == "none":
            config["branding"]["logo"]["enabled"] = False
        
        # Save job-specific config
        job_config = job_dir / "settings.yaml"
        with open(job_config, "w") as f:
            yaml.dump(config, f)
        
        # Run pipeline scripts
        scripts_dir = BASE_DIR / "scripts"
        output_dir = BASE_DIR / "output"
        
        # Copy job-specific config to output directory for render script
        output_config = output_dir / "settings.yaml"
        shutil.copy(job_config, output_config)
        
        # Stage 1: Generate script
        JOBS[job_id]["stage"] = "Creating script..."
        JOBS[job_id]["progress"] = 20
        
        cmd = [sys.executable, str(scripts_dir / "make_script.py"), topic]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=120)
        print(f"✅ Script generated: {len(result.stdout)} chars")
        
        # Stage 2: Generate voice
        JOBS[job_id]["stage"] = "Synthesizing voice..."
        JOBS[job_id]["progress"] = 40
        cmd = [sys.executable, str(scripts_dir / "make_voice.py")]
        subprocess.run(cmd, check=True, capture_output=True)
        
        # Stage 3: Generate captions based on selected style
        JOBS[job_id]["stage"] = "Creating captions..."
        JOBS[job_id]["progress"] = 55
        
        if caption_style == "bounce":
            caption_script = "make_captions_bounce.py"
        elif caption_style == "color_box":
            caption_script = "make_captions_color_box.py"
        elif caption_style == "karaoke":
            caption_script = "make_captions_karaoke.py"
        else:
            caption_script = "make_captions_bounce.py"  # Default
        
        if caption_style != "none":
            cmd = [sys.executable, str(scripts_dir / caption_script)]
            subprocess.run(cmd, check=True, capture_output=True)
        
        # Stage 4: Fetch or handle content based on type
        JOBS[job_id]["stage"] = "Collecting content..."
        JOBS[job_id]["progress"] = 70
        
        # Check if user uploaded content files
        uploaded_images = JOBS[job_id].get("image_paths", [])
        uploaded_videos = JOBS[job_id].get("video_paths", [])
        
        if uploaded_images:
            # Copy uploaded images to images/ directory
            images_dir = BASE_DIR / "images"
            images_dir.mkdir(exist_ok=True)
            
            # Clear existing images
            for img in images_dir.glob("img_*.*"):
                img.unlink()
            
            # Copy uploaded files
            for idx, src_path in enumerate(uploaded_images):
                src = Path(src_path)
                dst = images_dir / f"img_{idx+1:02d}{src.suffix}"
                shutil.copy(src, dst)
            
        if uploaded_videos:
            # Copy uploaded videos to videos/ directory
            videos_dir = BASE_DIR / "videos"
            videos_dir.mkdir(exist_ok=True)
            
            # Clear existing videos
            for vid in videos_dir.glob("video_*.mp4"):
                vid.unlink()
            
            # Copy uploaded files
            for idx, src_path in enumerate(uploaded_videos):
                src = Path(src_path)
                dst = videos_dir / f"video_{idx+1:02d}.mp4"
                shutil.copy(src, dst)
        
        # Auto-download if no uploads provided
        if not uploaded_images and content_type in ["images", "combo", "upload_both"]:
            # Auto-download images
            cmd = [sys.executable, str(scripts_dir / "make_images.py")]
            subprocess.run(cmd, check=True, capture_output=True)
        
        if not uploaded_videos and content_type in ["videos", "combo", "upload_both"]:
            # Video fetching (if implemented)
            cmd = [sys.executable, str(scripts_dir / "make_videos.py")]
            try:
                subprocess.run(cmd, check=True, capture_output=True)
            except:
                pass  # Fallback to images if video script doesn't exist
        
        # Stage 5: Render video based on content type
        JOBS[job_id]["stage"] = "Rendering video..."
        JOBS[job_id]["progress"] = 85
        
        # Choose the appropriate render script based on content_type
        if content_type in ["videos", "upload_videos"]:
            render_script = "make_video_render_clips.py"
        elif content_type in ["combo", "upload_both"]:
            render_script = "make_video_render_combo.py"
        else:
            render_script = "make_video_render.py"
        
        cmd = [sys.executable, str(scripts_dir / render_script), platform]
        subprocess.run(cmd, check=True, capture_output=True)
        
        # Copy final video to job directory
        final_video = output_dir / "final.mp4"
        job_video = job_dir / "video.mp4"
        
        if final_video.exists():
            shutil.copy(final_video, job_video)
            
            # Add to showcase
            add_to_showcase(job_video, job_id)
            
            JOBS[job_id]["status"] = "completed"
            JOBS[job_id]["stage"] = "Complete!"
            JOBS[job_id]["progress"] = 100
            JOBS[job_id]["video_path"] = str(job_video)
            JOBS[job_id]["completed_at"] = datetime.now().isoformat()
        else:
            raise FileNotFoundError("Video rendering failed")
            
    except subprocess.CalledProcessError as e:
        error_msg = f"Command failed: {e.stderr if e.stderr else str(e)}"
        print(f"Pipeline error: {error_msg}")
        JOBS[job_id]["status"] = "failed"
        JOBS[job_id]["stage"] = "Error occurred"
        JOBS[job_id]["progress"] = 0
        JOBS[job_id]["error"] = error_msg
    except Exception as e:
        print(f"Pipeline error: {str(e)}")
        JOBS[job_id]["status"] = "failed"
        JOBS[job_id]["stage"] = f"Error: {str(e)}"
        JOBS[job_id]["progress"] = 0
        JOBS[job_id]["error"] = str(e)

@app.route("/")
def index():
    """Serve landing page"""
    return render_template("landing.html")

@app.route("/create")
def create():
    """Serve video creation page"""
    return render_template("index.html")

@app.route("/static/<path:filename>")
def serve_static(filename):
    """Serve static files"""
    static_dir = BASE_DIR / "static"
    return send_from_directory(static_dir, filename)

@app.route("/api/generate", methods=["POST"])
def generate_video():
    """Start video generation job"""
    try:
        # Safely determine if request is JSON or form data
        logo_file = None
        image_files = []
        video_files = []
        data = {}
        
        # Try to get form data first (for file uploads)
        try:
            if request.form:
                data = request.form.to_dict()
                logo_file = request.files.get('logo_file')
                image_files = request.files.getlist('image_files')
                video_files = request.files.getlist('video_files')
        except Exception:
            pass
        
        # If no form data, try JSON
        if not data:
            try:
                data = request.get_json(force=True, silent=True) or {}
            except Exception:
                data = {}
        
        topic = data.get("topic", "").strip()
        platform = data.get("platform", "tiktok")
        style = data.get("style", "viral_facts")
        voice = data.get("voice", "en-US-GuyNeural")
        duration = int(data.get("duration", 25))
        transition = data.get("transition", "fade")
        logo_option = data.get("logo_option", "none")
        caption_style = data.get("caption_style", "bounce")
        content_type = data.get("content_type", "images")
        
        if not topic:
            return jsonify({"error": "Topic is required"}), 400
        
        # Calculate reasonable limits based on duration
        # Images: minimum 3 seconds per image
        max_images = max(3, duration // 3)
        # Videos: minimum 3 seconds per video  
        max_videos = max(2, duration // 3)
        
        # Validate upload counts
        if image_files and len(image_files) > max_images:
            return jsonify({"error": f"Too many images. Maximum {max_images} images for {duration}s video (min 3s per image)"}), 400
        
        if video_files and len(video_files) > max_videos:
            return jsonify({"error": f"Too many videos. Maximum {max_videos} videos for {duration}s video (min 3s per video)"}), 400
        
        # Create job
        job_id = str(uuid.uuid4())
        job_dir = JOBS_DIR / job_id
        job_dir.mkdir(exist_ok=True)
        
        # Handle uploaded logo
        uploaded_logo_path = None
        if logo_file and logo_option == "upload":
            # Validate file type
            allowed_extensions = {'.png', '.jpg', '.jpeg'}
            file_ext = Path(logo_file.filename).suffix.lower()
            if file_ext in allowed_extensions:
                uploaded_logo_path = job_dir / f"logo{file_ext}"
                logo_file.save(str(uploaded_logo_path))
        
        # Handle uploaded content files (images or videos)
        uploaded_image_paths = []
        uploaded_video_paths = []
        
        # File size limits (in bytes)
        MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB per image
        MAX_VIDEO_SIZE = 100 * 1024 * 1024  # 100MB per video
        
        if image_files and content_type in ['upload_images', 'upload_both']:
            content_dir = job_dir / "images"
            content_dir.mkdir(exist_ok=True)
            
            for idx, file in enumerate(image_files):
                # Check file size
                file.seek(0, 2)  # Seek to end
                file_size = file.tell()
                file.seek(0)  # Reset to beginning
                
                if file_size > MAX_IMAGE_SIZE:
                    return jsonify({"error": f"Image '{file.filename}' is too large. Max 10MB per image."}), 400
                
                allowed_ext = {'.jpg', '.jpeg', '.png'}
                file_ext = Path(file.filename).suffix.lower()
                if file_ext in allowed_ext:
                    file_path = content_dir / f"{idx:02d}{file_ext}"
                    file.save(str(file_path))
                    uploaded_image_paths.append(str(file_path))
        
        if video_files and content_type in ['upload_videos', 'upload_both']:
            content_dir = job_dir / "videos"
            content_dir.mkdir(exist_ok=True)
            
            for idx, file in enumerate(video_files):
                # Check file size
                file.seek(0, 2)  # Seek to end
                file_size = file.tell()
                file.seek(0)  # Reset to beginning
                
                if file_size > MAX_VIDEO_SIZE:
                    return jsonify({"error": f"Video '{file.filename}' is too large. Max 100MB per video."}), 400
                
                allowed_ext = {'.mp4'}
                file_ext = Path(file.filename).suffix.lower()
                if file_ext in allowed_ext:
                    file_path = content_dir / f"{idx:02d}.mp4"
                    file.save(str(file_path))
                    uploaded_video_paths.append(str(file_path))
        
        JOBS[job_id] = {
            "id": job_id,
            "topic": topic,
            "platform": platform,
            "style": style,
            "duration": duration,
            "transition": transition,
            "logo_option": logo_option,
            "logo_path": str(uploaded_logo_path) if uploaded_logo_path else None,
            "caption_style": caption_style,
            "content_type": content_type,
            "image_paths": uploaded_image_paths,
            "video_paths": uploaded_video_paths,
            "status": "queued",
            "stage": "Initializing...",
            "progress": 0,
            "created_at": datetime.now().isoformat()
        }
        
        # Start processing in background thread
        thread = threading.Thread(
            target=run_pipeline_async,
            args=(job_id, topic, platform, style, voice, duration, transition, caption_style, content_type, logo_option)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({"job_id": job_id, "status": "queued"})
        
    except Exception as e:
        return jsonify({"error": f"Upload failed: {str(e)}"}), 400

@app.route("/api/status/<job_id>", methods=["GET"])
def get_status(job_id):
    """Get job status"""
    if job_id not in JOBS:
        return jsonify({"error": "Job not found"}), 404
    
    return jsonify(JOBS[job_id])

@app.route("/api/download/<job_id>", methods=["GET"])
def download_video(job_id):
    """Download completed video"""
    # Try to get from JOBS dict first
    if job_id in JOBS:
        job = JOBS[job_id]
        if job["status"] != "completed":
            return jsonify({"error": "Video not ready"}), 400
        video_path = Path(job["video_path"])
    else:
        # If not in JOBS dict, try to find the video file directly
        video_path = JOBS_DIR / job_id / "video.mp4"
    
    if not video_path.exists():
        return jsonify({"error": "Video file not found"}), 404
    
    return send_file(
        video_path,
        mimetype="video/mp4",
        as_attachment=True,
        download_name="video.mp4"
    )

@app.route("/api/video/<job_id>", methods=["GET"])
def stream_video(job_id):
    """Stream video for preview (not as download)"""
    # Try to get from JOBS dict first
    if job_id in JOBS:
        job = JOBS[job_id]
        if job["status"] != "completed":
            return jsonify({"error": "Video not ready"}), 400
        video_path = Path(job["video_path"])
    else:
        # If not in JOBS dict, try to find the video file directly
        video_path = JOBS_DIR / job_id / "video.mp4"
    
    if not video_path.exists():
        return jsonify({"error": "Video file not found"}), 404
    
    return send_file(
        video_path,
        mimetype="video/mp4",
        as_attachment=False  # Stream for preview, not download
    )

@app.route("/api/config", methods=["GET"])
def get_config():
    """Get available options for frontend"""
    return jsonify({
        "platforms": [
            {"id": "tiktok", "name": "TikTok", "aspect": "9:16"},
            {"id": "youtube_shorts", "name": "YouTube Shorts", "aspect": "9:16"},
            {"id": "instagram_reel", "name": "Instagram Reel", "aspect": "9:16"},
            {"id": "youtube", "name": "YouTube", "aspect": "16:9"},
            {"id": "instagram_feed", "name": "Instagram Feed", "aspect": "1:1"}
        ],
        "styles": [
            {"id": "viral_facts", "name": "Viral Facts", "desc": "Quick, engaging facts"},
            {"id": "story_time", "name": "Story Time", "desc": "Narrative storytelling"},
            {"id": "motivational", "name": "Motivational", "desc": "Inspiring content"},
            {"id": "educational", "name": "Educational", "desc": "Teaching content"}
        ],
        "transitions": [
            {"id": "fade", "name": "Fade"},
            {"id": "slideright", "name": "Slide Right"},
            {"id": "slideleft", "name": "Slide Left"},
            {"id": "wiperight", "name": "Wipe Right"},
            {"id": "dissolve", "name": "Dissolve"},
            {"id": "circleopen", "name": "Circle Open"},
            {"id": "kenburns", "name": "Ken Burns (Zoom/Pan)"}
        ],
        "durations": [15, 25, 30, 45, 60, 90]
    })

@app.route("/api/showcase", methods=["GET"])
def get_showcase():
    """Get showcase videos"""
    cleanup_old_showcase_videos()
    showcase = load_showcase()
    return jsonify(showcase)  # Return all videos

if __name__ == "__main__":
    print("🚀 Starting EchoAI Web Server...")
    print("📱 Open http://localhost:5000 in your browser")
    app.run(debug=True, host="0.0.0.0", port=5000)
