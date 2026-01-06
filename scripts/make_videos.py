import re
import requests
from pathlib import Path
from collections import Counter
import random
import time
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"
VIDEO_DIR = BASE_DIR / "videos"
CONFIG_PATH = BASE_DIR / "config" / "settings.yaml"

SCRIPT = OUTPUT_DIR / "script.txt"

VIDEO_DIR.mkdir(exist_ok=True)

# Track Vecteezy downloads (500/month free tier limit)
VECTEEZY_DOWNLOADS = 0

def load_config():
    """Load settings from YAML config"""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

# Generic fallback keywords if topic words fail
FALLBACKS = [
    "lifestyle",
    "smartphone",
    "people",
    "modern life",
    "urban",
    "daily routine"
]

def extract_keywords(text: str, max_words=6):
    # Remove quotes and clean text
    text = text.replace('"', '').replace("'", '')
    
    # Find all words (4+ letters)
    words = re.findall(r"[a-zA-Z]{4,}", text.lower())
    common = Counter(words)
    
    # Expanded stopwords
    stopwords = {
        "that", "this", "with", "from", "they", "their", "have", "there",
        "about", "would", "could", "people", "because", "which", "when",
        "just", "know", "ever", "those", "thing", "right", "what", "your",
        "some", "been", "like", "were", "said", "each", "them", "than",
        "many", "more", "make", "made", "then", "into", "only", "other",
        "also", "these", "tell", "gets", "gives", "kind", "happen", "youll",
        "youre", "never", "believe"
    }
    
    # Extract meaningful keywords
    keywords = [
        w for w, _ in common.most_common(20)  # Get top 20 first
        if w not in stopwords and len(w) >= 4
    ][:max_words]
    
    # If not enough keywords, add topic-relevant defaults
    if len(keywords) < max_words:
        topic_words = ["lifestyle", "moment", "people", "daily", "experience"]
        for word in topic_words:
            if word not in keywords:
                keywords.append(word)
                if len(keywords) >= max_words:
                    break
    
    return keywords[:max_words]

def fetch_video_pexels(keyword: str, out_path: Path) -> bool:
    """Fetch video from Pexels Videos API"""
    try:
        config = load_config()
        api_key = config.get("pexels", {}).get("api_key", "")
        
        if not api_key:
            print("    No Pexels API key found")
            return False
        
        search_url = "https://api.pexels.com/videos/search"
        headers = {"Authorization": api_key}
        params = {
            "query": keyword,
            "orientation": "portrait",
            "size": "large",
            "per_page": 20
        }
        
        r = requests.get(search_url, headers=headers, params=params, timeout=10)
        if r.status_code != 200:
            print(f"    Pexels API returned status {r.status_code}")
            return False
            
        data = r.json()
        if not data.get("videos"):
            print(f"    No videos found for '{keyword}'")
            return False
        
        # Get a random video from results
        video = random.choice(data["videos"])
        
        # Find HD portrait video file (1080x1920 or closest)
        video_files = video.get("video_files", [])
        
        # Filter for portrait orientation (height > width)
        portrait_files = [
            vf for vf in video_files
            if vf.get("height", 0) > vf.get("width", 0)
        ]
        
        if not portrait_files:
            print(f"    No portrait videos found for '{keyword}'")
            return False
        
        # Sort by quality and pick the best HD one (not too large)
        portrait_files.sort(key=lambda x: x.get("height", 0), reverse=True)
        
        # Prefer videos around 1080x1920 or 720x1280
        best_file = None
        for vf in portrait_files:
            height = vf.get("height", 0)
            if 1000 <= height <= 2000:  # HD range
                best_file = vf
                break
        
        # Fallback to first portrait video if no HD found
        if not best_file:
            best_file = portrait_files[0]
        
        video_url = best_file.get("link")
        if not video_url:
            return False
        
        print(f"   Downloading {best_file.get('width')}x{best_file.get('height')} video...")
        
        # Download the video
        vid_response = requests.get(video_url, timeout=30, stream=True)
        
        if vid_response.status_code == 200:
            # Stream download for large files
            with open(out_path, 'wb') as f:
                for chunk in vid_response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Check file size (should be at least 100KB)
            if out_path.stat().st_size > 100000:
                size_mb = out_path.stat().st_size / (1024 * 1024)
                print(f"   SOURCE: PEXELS | Size: {size_mb:.1f}MB | Video ID: {video.get('id', 'unknown')}")
                return True
            else:
                out_path.unlink()
                return False
            
    except Exception as e:
        print(f"    Pexels Error: {e}")
    
    return False

def fetch_video_vecteezy(keyword: str, out_path: Path) -> bool:
    """Fetch license-safe video from Vecteezy API
    
    Free tier: 500 downloads/month of free content (TikTok safe!)
    """
    global VECTEEZY_DOWNLOADS
    
    try:
        config = load_config()
        api_key = config.get("vecteezy", {}).get("api_key", "")
        account_id = config.get("vecteezy", {}).get("account_id", "")
        
        if not api_key or not account_id:
            return False
        
        # Check account quota first
        quota_url = f"https://api.vecteezy.com/v2/{account_id}/account/info"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        try:
            quota_r = requests.get(quota_url, headers=headers, timeout=5)
            if quota_r.status_code == 200:
                quota_data = quota_r.json()
                current = quota_data.get("current", {}).get("download", {})
                used = current.get("call_count", 0)
                total = current.get("call_limit", 500)
                remaining = total - used
                print(f"   Vecteezy quota: {used}/{total} used, {remaining} remaining")
                
                if remaining <= 0:
                    print(f"    Vecteezy quota exceeded! Skipping.")
                    return False
        except:
            pass  # Continue anyway if quota check fails
        
        # Search for free videos (license='free' ensures TikTok safety)
        search_url = f"https://api.vecteezy.com/v2/{account_id}/resources"
        params = {
            "term": keyword,  # REQUIRED: search term
            "content_type": "video",  # REQUIRED: video content type
            "license_type": "commercial",  # commercial or editorial
            "orientation": "vertical",  # vertical = portrait for TikTok
            "page": 1,
            "per_page": 20
        }
        
        r = requests.get(search_url, headers=headers, params=params, timeout=10)
        
        if r.status_code != 200:
            return False
        
        data = r.json()
        resources = data.get("resources", [])
        
        if not resources:
            return False
        
        # Get a random resource from results
        resource = random.choice(resources)
        resource_id = resource.get("id")
        resource_title = resource.get("title", "untitled")[:40]
        
        if not resource_id:
            return False
        
        # Get download URL
        download_url = f"https://api.vecteezy.com/v2/{account_id}/resources/{resource_id}/download"
        download_params = {
            "size": "hd",  # HD quality
            "file_type": "mp4"
        }
        
        r = requests.get(download_url, headers=headers, params=download_params, timeout=15)
        if r.status_code != 200:
            return False
        
        download_data = r.json()
        video_url = download_data.get("url")
        
        if not video_url:
            return False
        
        # Download the video
        video_response = requests.get(video_url, timeout=30, stream=True)
        
        if video_response.status_code == 200:
            # Stream download for large video files
            with open(out_path, 'wb') as f:
                for chunk in video_response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            if out_path.stat().st_size > 50000:  # At least 50KB
                VECTEEZY_DOWNLOADS += 1
                size_mb = out_path.stat().st_size / (1024 * 1024)
                print(f"   SOURCE: VECTEEZY | Size: {size_mb:.1f}MB | Resource: {resource_title} (ID: {resource_id})")
                return True
            else:
                out_path.unlink(missing_ok=True)
                return False
                
    except Exception as e:
        print(f"    Vecteezy Error: {e}")
    
    return False

def main():
    if not SCRIPT.exists():
        raise FileNotFoundError("script.txt not found")

    # Check if videos already exist (from user uploads)
    existing_videos = list(VIDEO_DIR.glob("video_*.mp4"))
    if existing_videos:
        print(f" Using {len(existing_videos)} existing videos (user uploaded)")
        return

    text = SCRIPT.read_text(encoding="utf-8")
    keywords = extract_keywords(text)

    print(" Fetching relevant videos (Vecteezy  Pexels fallback):")
    print(f"Keywords: {keywords}")

    VIDEO_DIR.mkdir(exist_ok=True)

    video_index = 1
    max_videos = 6
    
    for kw in keywords:
        if video_index > max_videos:
            break
            
        print(f"\n Searching video: '{kw}'")
        
        out_path = VIDEO_DIR / f"video_{video_index:02d}.mp4"
        success = False
        
        # Try Vecteezy first (license-safe videos)
        if fetch_video_vecteezy(kw, out_path):
            success = True
        
        # Try Pexels as fallback
        if not success:
            print(f"   Trying Pexels fallback")
            if fetch_video_pexels(kw, out_path):
                success = True
        
        # Try fallback keyword with Pexels
        if not success:
            fallback = random.choice(FALLBACKS)
            print(f"   Trying fallback keyword: '{fallback}'")
            if fetch_video_pexels(fallback, out_path):
                success = True
        
        if success:
            video_index += 1
        else:
            print(f"   Failed to download video for '{kw}'")
        
        time.sleep(1)  # Rate limiting (videos are larger)
    
    # Fill remaining slots with fallback searches if needed
    while video_index <= max_videos:
        print(f"\n Filling slot {video_index} with fallback video")
        out_path = VIDEO_DIR / f"video_{video_index:02d}.mp4"
        fallback = random.choice(FALLBACKS)
        
        if fetch_video_pexels(fallback, out_path):
            video_index += 1
        else:
            print(f"    Skipping slot {video_index} - no video available")
            video_index += 1
        
        time.sleep(1)

    actual_count = len(list(VIDEO_DIR.glob("video_*.mp4")))
    print(f"\n Downloaded {actual_count} videos to videos/")
    
    if VECTEEZY_DOWNLOADS > 0:
        print(f" Vecteezy downloads this run: {VECTEEZY_DOWNLOADS}")
    
    if actual_count == 0:
        print("  WARNING: No videos were downloaded!")
        print("    The pipeline will fail at video rendering step.")

if __name__ == "__main__":
    main()
