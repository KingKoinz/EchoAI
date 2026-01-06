import re
import requests
from pathlib import Path
from collections import Counter
import random
import time
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"
IMG_DIR = BASE_DIR / "images"
CONFIG_PATH = BASE_DIR / "config" / "settings.yaml"

SCRIPT = OUTPUT_DIR / "script.txt"

IMG_DIR.mkdir(exist_ok=True)

# Track Vecteezy downloads (500/month free tier limit)
VECTEEZY_DOWNLOADS = 0

def load_config():
    """Load settings from YAML config"""
    # Check for job-specific config first
    job_config = OUTPUT_DIR / "settings.yaml"
    config_path = job_config if job_config.exists() else CONFIG_PATH
    with open(config_path, "r", encoding="utf-8") as f:
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

def fetch_image_unsplash(keyword: str, out_path: Path) -> bool:
    """Fetch image from Unsplash API
    
    Free tier: 50 requests/hour (demo apps)
    Production: 5000 requests/hour (after submission)
    """
    try:
        config = load_config()
        access_key = config.get("unsplash", {}).get("access_key", "")
        
        if not access_key:
            return False
        
        search_url = "https://api.unsplash.com/search/photos"
        headers = {"Authorization": f"Client-ID {access_key}"}
        params = {
            "query": keyword,
            "orientation": "portrait",
            "per_page": 20,
            "content_filter": "high"  # Filter adult content
        }
        
        r = requests.get(search_url, headers=headers, params=params, timeout=10)
        if r.status_code != 200:
            return False
            
        data = r.json()
        results = data.get("results", [])
        
        if not results:
            return False
        
        # Get a random photo from results
        photo = random.choice(results)
        photo_id = photo.get("id", "unknown")
        photographer = photo.get("user", {}).get("name", "Unknown")
        
        # Download the regular size image (1080px width)
        img_url = photo["urls"]["regular"]
        img_response = requests.get(img_url, timeout=15)
        
        if img_response.status_code == 200 and len(img_response.content) > 5000:
            out_path.write_bytes(img_response.content)
            print(f"   SOURCE: UNSPLASH | Photo: {photo_id} by {photographer}")
            
            # Trigger download tracking (required by Unsplash API terms)
            download_url = photo.get("links", {}).get("download_location")
            if download_url:
                try:
                    requests.get(download_url, headers=headers, timeout=5)
                except:
                    pass  # Silent fail on tracking
            
            return True
            
    except Exception as e:
        print(f"    Unsplash Error: {e}")
    
    return False

def fetch_image_pexels(keyword: str, out_path: Path) -> bool:
    """Fetch image from Pexels API"""
    try:
        config = load_config()
        api_key = config.get("pexels", {}).get("api_key", "")
        
        if not api_key:
            return False
        
        search_url = "https://api.pexels.com/v1/search"
        headers = {"Authorization": api_key}
        params = {
            "query": keyword,
            "orientation": "portrait",
            "size": "large",
            "per_page": 20
        }
        
        r = requests.get(search_url, headers=headers, params=params, timeout=10)
        if r.status_code != 200:
            return False
            
        data = r.json()
        if not data.get("photos"):
            return False
        
        # Get a random photo from results
        photo = random.choice(data["photos"])
        photo_id = photo.get("id", "unknown")
        
        # Download the portrait image
        img_url = photo["src"]["portrait"]
        img_response = requests.get(img_url, timeout=15)
        
        if img_response.status_code == 200 and len(img_response.content) > 5000:
            out_path.write_bytes(img_response.content)
            print(f"   SOURCE: PEXELS | Photo ID: {photo_id}")
            return True
            
    except Exception as e:
        print(f"    Pexels Error: {e}")
    
    return False

def fetch_image_vecteezy(keyword: str, out_path: Path) -> bool:
    """Fetch license-safe image from Vecteezy API
    
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
        
        # Search for free photos (license='free' ensures TikTok safety)
        search_url = f"https://api.vecteezy.com/v2/{account_id}/resources"
        headers = {"Authorization": f"Bearer {api_key}"}
        params = {
            "term": keyword,  # REQUIRED: search term
            "content_type": "photo",  # REQUIRED: photo, png, psd, svg, vector, or video
            "license_type": "commercial",  # commercial or editorial
            "orientation": "vertical",  # vertical = portrait
            "page": 1,
            "per_page": 20
        }
        
        r = requests.get(search_url, headers=headers, params=params, timeout=10)
        if r.status_code != 200:
            print(f"    Vecteezy search error: HTTP {r.status_code}")
            print(f"     {r.text[:150]}")
            return False
        
        data = r.json()
        resources = data.get("resources", [])
        
        if not resources:
            print(f"    No Vecteezy results for '{keyword}'")
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
            "size": "large",  # large size for good quality
            "file_type": "jpg"
        }
        
        r = requests.get(download_url, headers=headers, params=download_params, timeout=15)
        if r.status_code != 200:
            return False
        
        download_data = r.json()
        img_url = download_data.get("url")
        
        if not img_url:
            return False
        
        # Download the image
        img_response = requests.get(img_url, timeout=15)
        if img_response.status_code == 200 and len(img_response.content) > 5000:
            out_path.write_bytes(img_response.content)
            VECTEEZY_DOWNLOADS += 1
            print(f"   SOURCE: VECTEEZY | Resource: {resource_title} (ID: {resource_id})")
            return True
                
    except Exception as e:
        print(f"    Vecteezy Error: {e}")
    
    return False

def fetch_image_lorem_picsum(keyword: str, out_path: Path, seed: int) -> bool:
    """Fetch image from Lorem Picsum with seed for consistency"""
    try:
        # Use seed to get consistent but different images
        url = f"https://picsum.photos/seed/{keyword}{seed}/1080/1920"
        r = requests.get(url, timeout=10)
        if r.status_code == 200 and len(r.content) > 5000:
            out_path.write_bytes(r.content)
            print(f"   SOURCE: PICSUM | Seed: {keyword}{seed}")
            return True
    except Exception:
        pass
    return False

def main():
    if not SCRIPT.exists():
        raise FileNotFoundError("script.txt not found")

    # Check if images already exist (from user uploads)
    existing_images = list(IMG_DIR.glob("img_*.jpg")) + list(IMG_DIR.glob("img_*.png")) + list(IMG_DIR.glob("img_*.jpeg"))
    if existing_images:
        print(f" Using {len(existing_images)} existing images (user uploaded)")
        return

    text = SCRIPT.read_text(encoding="utf-8")
    keywords = extract_keywords(text)

    print(" Fetching relevant images (Unsplash → Vecteezy → Pexels → Picsum):")
    print(f"Keywords: {keywords}")

    IMG_DIR.mkdir(exist_ok=True)

    img_index = 1
    max_images = 6
    seed_base = int(time.time())
    
    for kw in keywords:
        if img_index > max_images:
            break
            
        print(f"\n Searching: '{kw}'")
        
        out_path = IMG_DIR / f"img_{img_index:02d}.jpg"
        success = False
        
        # Try Unsplash first (high quality, free)
        if fetch_image_unsplash(kw, out_path):
            success = True
        
        # Try Vecteezy second (license-safe images)
        if not success:
            print(f"   Trying Vecteezy fallback")
            if fetch_image_vecteezy(kw, out_path):
                success = True
        
        # Try Pexels third
        if not success:
            print(f"   Trying Pexels fallback")
            if fetch_image_pexels(kw, out_path):
                success = True
        
        # Try fallback keyword with Pexels
        if not success:
            fallback = random.choice(FALLBACKS)
            print(f"   Trying fallback keyword: '{fallback}'")
            if fetch_image_pexels(fallback, out_path):
                success = True
        
        # Last resort: Picsum with keyword seed
        if not success:
            print(f"   Using Picsum (keyword-seeded)")
            if fetch_image_lorem_picsum(kw, out_path, seed_base):
                success = True
        
        if success:
            img_index += 1
        
        time.sleep(0.5)  # Rate limiting
    
    # Fill remaining slots with Picsum if needed
    while img_index <= max_images:
        print(f"\n Filling slot {img_index} with Picsum")
        out_path = IMG_DIR / f"img_{img_index:02d}.jpg"
        fallback = random.choice(FALLBACKS)
        fetch_image_lorem_picsum(fallback, out_path, seed_base + img_index * 100)
        img_index += 1
        time.sleep(0.3)

    print(f"\n Downloaded {max_images} images to images/")
    
    if VECTEEZY_DOWNLOADS > 0:
        print(f" Vecteezy downloads this run: {VECTEEZY_DOWNLOADS}")

if __name__ == "__main__":
    main()


