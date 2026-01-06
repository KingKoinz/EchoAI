"""
Download videos from Vecteezy API based on script content.
Vecteezy has free, license-safe videos perfect for TikTok!

Free tier: 500 downloads/month
"""
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

# Track downloads
VECTEEZY_DOWNLOADS = 0

def load_config():
    """Load settings from YAML config"""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

# Generic fallback keywords if topic words fail
FALLBACKS = [
    "lifestyle",
    "people",
    "modern life",
    "urban",
    "daily routine",
    "technology"
]

def extract_keywords(text: str, max_words=6):
    """Extract relevant keywords from script text"""
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
        w for w, _ in common.most_common(20)
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
            print("    Vecteezy API credentials not configured")
            return False
        
        # Check account quota first
        quota_url = f"https://api.vecteezy.com/v2/{account_id}/account/info"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        try:
            quota_r = requests.get(quota_url, headers=headers, timeout=5)
            if quota_r.status_code == 200:
                quota_data = quota_r.json()
                remaining = quota_data.get("downloads_remaining", 0)
                total = quota_data.get("downloads_total", 500)
                used = total - remaining
                print(f"   Vecteezy quota: {used}/{total} used, {remaining} remaining")
                
                if remaining <= 0:
                    print(f"    Vecteezy quota exceeded! Skipping.")
                    return False
        except Exception as e:
            print(f"    Could not check quota: {e}")
            pass  # Continue anyway if quota check fails
        
        # Search for free videos (license='free' ensures TikTok safety)
        search_url = f"https://api.vecteezy.com/v2/{account_id}/resources"
        params = {
            "query": keyword,
            "resource_type": "video",  # VIDEOS!
            "license": "free",  # IMPORTANT: only free/safe content
            "orientation": "portrait",  # Portrait for TikTok
            "page": 1,
            "limit": 20
        }
        
        print(f"   Searching Vecteezy videos: '{keyword}'...")
        r = requests.get(search_url, headers=headers, params=params, timeout=10)
        
        if r.status_code != 200:
            print(f"    Search failed: HTTP {r.status_code}")
            return False
        
        data = r.json()
        resources = data.get("data", [])
        
        if not resources:
            print(f"    No videos found for '{keyword}'")
            return False
        
        print(f"   Found {len(resources)} videos")
        
        # Get a random resource from results
        resource = random.choice(resources)
        resource_id = resource.get("id")
        resource_title = resource.get("title", "untitled")
        
        if not resource_id:
            return False
        
        print(f"   Downloading: '{resource_title[:50]}'...")
        
        # Get download URL
        download_url = f"https://api.vecteezy.com/v2/{account_id}/resources/{resource_id}/download"
        download_params = {
            "size": "hd",  # HD quality
            "file_type": "mp4"
        }
        
        r = requests.get(download_url, headers=headers, params=download_params, timeout=15)
        if r.status_code != 200:
            print(f"    Download request failed: HTTP {r.status_code}")
            return False
        
        download_data = r.json()
        video_url = download_data.get("url")
        
        if not video_url:
            print(f"    No download URL in response")
            return False
        
        # Download the video
        print(f"    Fetching video file...")
        video_response = requests.get(video_url, timeout=30, stream=True)
        
        if video_response.status_code == 200:
            # Stream download for large video files
            total_size = 0
            with open(out_path, 'wb') as f:
                for chunk in video_response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    total_size += len(chunk)
            
            if total_size > 50000:  # At least 50KB
                size_mb = total_size / (1024 * 1024)
                print(f"   Downloaded {size_mb:.1f}MB video")
                VECTEEZY_DOWNLOADS += 1
                return True
            else:
                print(f"    Downloaded file too small: {total_size} bytes")
                out_path.unlink(missing_ok=True)
                return False
                
    except Exception as e:
        print(f"    Vecteezy Error: {e}")
    
    return False

def main():
    if not SCRIPT.exists():
        raise FileNotFoundError("script.txt not found. Run make_script.py first.")

    text = SCRIPT.read_text(encoding="utf-8")
    keywords = extract_keywords(text, max_words=6)

    print(" Fetching relevant videos from Vecteezy:")
    print(f"Keywords: {keywords}\n")

    VIDEO_DIR.mkdir(exist_ok=True)

    video_index = 1
    max_videos = 6
    successful_downloads = 0
    
    for kw in keywords:
        if successful_downloads >= max_videos:
            break
            
        print(f"\n{'='*60}")
        print(f"Video {video_index}/{max_videos} - Keyword: '{kw}'")
        print('='*60)
        
        out_path = VIDEO_DIR / f"video_{video_index:02d}.mp4"
        
        if fetch_video_vecteezy(kw, out_path):
            successful_downloads += 1
            video_index += 1
        else:
            # Try fallback keyword
            fallback = random.choice(FALLBACKS)
            print(f"\n   Trying fallback: '{fallback}'")
            if fetch_video_vecteezy(fallback, out_path):
                successful_downloads += 1
                video_index += 1
        
        time.sleep(0.5)  # Rate limiting
    
    print(f"\n{'='*60}")
    print(f" Downloaded {successful_downloads}/{max_videos} videos to videos/")
    
    if VECTEEZY_DOWNLOADS > 0:
        print(f" Vecteezy downloads this run: {VECTEEZY_DOWNLOADS}")
    
    if successful_downloads < max_videos:
        print(f"  Only got {successful_downloads} videos. Consider using Pexels as fallback.")

if __name__ == "__main__":
    main()
