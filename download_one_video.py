"""Quick script to download just 1 video from Pexels"""
import requests
import yaml
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config" / "settings.yaml"
VIDEO_DIR = BASE_DIR / "videos"

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

config = load_config()
api_key = config.get("pexels", {}).get("api_key", "")

if not api_key:
    print("No Pexels API key found")
    exit(1)

# Search for generic vertical video
keyword = "business"
print(f"Searching Pexels for '{keyword}'...")

url = f"https://api.pexels.com/videos/search"
headers = {"Authorization": api_key}
params = {
    "query": keyword,
    "orientation": "portrait",
    "per_page": 5
}

r = requests.get(url, headers=headers, params=params, timeout=10)
data = r.json()

if not data.get("videos"):
    print("No videos found")
    exit(1)

# Get first video with vertical format
for vid in data["videos"]:
    for file in vid.get("video_files", []):
        if file.get("width", 0) < file.get("height", 0):  # Portrait
            video_url = file["link"]
            file_size_mb = file.get("file_size", 0) / (1024 * 1024)
            
            if file_size_mb > 20:  # Skip very large files
                continue
                
            print(f"Downloading {file_size_mb:.1f}MB video...")
            
            video_response = requests.get(video_url, stream=True, timeout=60)
            output_path = VIDEO_DIR / "video_03.mp4"
            
            with open(output_path, 'wb') as f:
                for chunk in video_response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            final_size = output_path.stat().st_size / (1024 * 1024)
            print(f"✅ Downloaded {final_size:.1f}MB to {output_path.name}")
            exit(0)

print("No suitable video found")
