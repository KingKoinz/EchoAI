"""
Download videos from Google using SerpAPI
"""
import re
import requests
from pathlib import Path
from collections import Counter
import yaml
import time

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"
VIDEO_DIR = BASE_DIR / "videos"
CONFIG_PATH = BASE_DIR / "config" / "settings.yaml"
SCRIPT = OUTPUT_DIR / "script.txt"

VIDEO_DIR.mkdir(exist_ok=True)

def load_config():
    """Load settings from YAML config"""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def extract_keywords(text: str, max_words=6):
    """Extract relevant keywords from script text"""
    text = text.replace('"', '').replace("'", '')
    words = re.findall(r"[a-zA-Z]{4,}", text.lower())
    common = Counter(words)
    
    stopwords = {
        "that", "this", "with", "from", "they", "their", "have", "there",
        "about", "would", "could", "people", "because", "which", "when",
        "just", "know", "ever", "those", "thing", "right", "what", "your",
        "some", "been", "like", "were", "said", "each", "them", "than",
        "many", "more", "make", "made", "then", "into", "only", "other",
        "also", "these", "tell", "gets", "gives", "kind", "happen"
    }
    
    relevant = [(word, count) for word, count in common.most_common(20) 
                if word not in stopwords]
    return [word for word, _ in relevant[:max_words]]

def fetch_videos_serpapi(keyword: str, api_key: str, num_videos=6):
    """
    Fetch video URLs from Google Videos using SerpAPI
    """
    try:
        # SerpAPI parameters for Google Videos
        params = {
            "engine": "google_videos",
            "q": keyword,
            "api_key": api_key,
            "num": num_videos
        }
        
        response = requests.get("https://serpapi.com/search.json", params=params, timeout=10)
        
        if response.status_code != 200:
            print(f"    SerpAPI returned status {response.status_code}")
            return []
        
        data = response.json()
        video_results = data.get("video_results", [])
        
        if not video_results:
            return []
        
        # Extract direct video links
        video_urls = []
        for result in video_results[:num_videos]:
            # Try to get direct mp4 link
            link = result.get("link", "")
            if link and (".mp4" in link or "video" in link):
                video_urls.append(link)
        
        return video_urls
        
    except Exception as e:
        print(f"    SerpAPI Error: {e}")
        return []

def download_video(url: str, out_path: Path) -> bool:
    """Download video from URL"""
    try:
        print(f"   Downloading from {url[:60]}...")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, stream=True, timeout=30)
        
        if response.status_code == 200:
            with open(out_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            size_mb = out_path.stat().st_size / (1024 * 1024)
            print(f"   Downloaded {size_mb:.1f}MB")
            return True
        else:
            print(f"    HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"    Download error: {e}")
        if out_path.exists():
            out_path.unlink()
        return False

def main():
    print(" Fetching videos from Google (SerpAPI):")
    
    if not SCRIPT.exists():
        print(" script.txt not found")
        return
    
    config = load_config()
    serpapi_key = config.get('serpapi', {}).get('api_key', '')
    
    if not serpapi_key:
        print(" ERROR: SerpAPI key not found in settings.yaml")
        return
    
    # Read script and extract keywords
    script_text = SCRIPT.read_text(encoding="utf-8")
    keywords = extract_keywords(script_text, max_words=6)
    
    print(f"Keywords: {keywords}\n")
    
    # Determine how many videos we need (based on audio length)
    audio_path = OUTPUT_DIR / "voice.wav"
    num_videos_needed = 6  # Default
    
    if audio_path.exists():
        import subprocess
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", 
                 "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", 
                 str(audio_path)],
                capture_output=True, text=True
            )
            audio_duration = float(result.stdout.strip())
            num_videos_needed = max(3, int(audio_duration / 9.0))
            print(f"  Audio: {audio_duration:.1f}s  Need {num_videos_needed} videos\n")
        except:
            pass
    
    # Download videos for each keyword
    video_count = 0
    
    for i, keyword in enumerate(keywords):
        if video_count >= num_videos_needed:
            break
        
        out_path = VIDEO_DIR / f"video_{video_count + 1:02d}.mp4"
        
        if out_path.exists():
            print(f" Video {video_count + 1} already exists: {out_path.name}")
            video_count += 1
            continue
        
        print(f"\n{'='*60}")
        print(f"Video {video_count + 1}/{num_videos_needed} - Keyword: '{keyword}'")
        print(f"{'='*60}")
        
        # Search for videos
        video_urls = fetch_videos_serpapi(keyword, serpapi_key, num_videos=3)
        
        if not video_urls:
            print(f"    No videos found for '{keyword}'")
            continue
        
        # Try each video URL until one works
        for url in video_urls:
            if download_video(url, out_path):
                video_count += 1
                time.sleep(1)  # Rate limiting
                break
        
        if not out_path.exists():
            print(f"    Failed to download video for '{keyword}'")
    
    print(f"\n\n{'='*60}")
    print(f" Downloaded {video_count}/{num_videos_needed} videos")
    print(f" Location: {VIDEO_DIR}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
