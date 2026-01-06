import re
import requests
from pathlib import Path
from collections import Counter
import random
import time

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"
IMG_DIR = BASE_DIR / "images"

SCRIPT = OUTPUT_DIR / "script.txt"

IMG_DIR.mkdir(exist_ok=True)

# Pixabay API key - Get free at https://pixabay.com/api/docs/
# Free tier: 5,000 requests/hour
PIXABAY_API_KEY = "48359187-12c835f6c4b6df7c6ba23c1c8"

# Pexels API key (backup)
PEXELS_API_KEY = "gVbB68MJ8YK0x4FGcJzKFT9cWiQYqP3hJ7O2R7ycnBLNGBE78wy2C7oy"

# Generic fallback keywords if topic words fail
FALLBACKS = [
    "social media",
    "phone screen", 
    "urban lifestyle",
    "modern life",
    "young people",
    "city life"
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
        if w not in stopwords and len(w) > 4  # Only longer words
    ]
    
    # If we don't have enough keywords, add some topic-related ones
    if len(keywords) < max_words:
        topic_words = ["night", "dark", "mystery", "shadow", "creepy"]
        for word in topic_words:
            if word not in keywords:
                keywords.append(word)
                if len(keywords) >= max_words:
                    break
    
    return keywords[:max_words]

def fetch_image_pixabay(keyword: str, out_path: Path) -> bool:
    """Fetch image from Pixabay API - Primary source"""
    try:
        search_url = "https://pixabay.com/api/"
        params = {
            "key": PIXABAY_API_KEY,
            "q": keyword,
            "image_type": "photo",
            "orientation": "vertical",
            "min_width": 1080,
            "min_height": 1920,
            "per_page": 20,
            "safesearch": "true"
        }
        
        r = requests.get(search_url, params=params, timeout=10)
        if r.status_code != 200:
            return False
            
        data = r.json()
        if not data.get("hits") or len(data["hits"]) == 0:
            return False
        
        # Get a random photo from results
        photo = random.choice(data["hits"])
        
        # Download the large image
        img_url = photo["largeImageURL"]
        img_response = requests.get(img_url, timeout=15)
        
        if img_response.status_code == 200 and len(img_response.content) > 5000:
            out_path.write_bytes(img_response.content)
            return True
            
    except Exception as e:
        print(f"    Pixabay Error: {e}")
    
    return False

def fetch_image_pexels(keyword: str, out_path: Path) -> bool:
    """Fetch image from Pexels API based on keyword"""
    try:
        # Search for photos matching keyword
        search_url = "https://api.pexels.com/v1/search"
        headers = {"Authorization": PEXELS_API_KEY}
        params = {
            "query": keyword,
            "orientation": "portrait",
            "size": "large",
            "per_page": 15
        }
        
        r = requests.get(search_url, headers=headers, params=params, timeout=10)
        if r.status_code != 200:
            return False
            
        data = r.json()
        if not data.get("photos"):
            return False
        
        # Get a random photo from results
        photo = random.choice(data["photos"])
        
        # Download the portrait image
        img_url = photo["src"]["portrait"]
        img_response = requests.get(img_url, timeout=15)
        
        if img_response.status_code == 200 and len(img_response.content) > 5000:
            out_path.write_bytes(img_response.content)
            return True
            
    except Exception as e:
        print(f"    Pexels Error: {e}")
    
    return False

def fetch_image_unsplash(keyword: str, out_path: Path) -> bool:
    """Fetch from Unsplash random API"""
    try:
        url = f"https://source.unsplash.com/1080x1920/?{keyword.replace(' ', ',')}"
        r = requests.get(url, timeout=10, allow_redirects=True)
        if r.status_code == 200 and len(r.content) > 5000:
            out_path.write_bytes(r.content)
            return True
    except Exception:
        pass
    return False

def fetch_image_picsum(out_path: Path, seed: int) -> bool:
    """Fallback to Picsum with seed"""
    try:
        url = f"https://picsum.photos/seed/{seed}/1080/1920"
        r = requests.get(url, timeout=10)
        if r.status_code == 200 and len(r.content) > 5000:
            out_path.write_bytes(r.content)
            return True
    except Exception:
        pass
    return False

def main():
    if not SCRIPT.exists():
        raise FileNotFoundError("script.txt not found")

    text = SCRIPT.read_text(encoding="utf-8")
    keywords = extract_keywords(text)

    print(" Fetching relevant images (Pixabay  Pexels  Picsum):")
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
        
        # Try Pixabay first (best quality, most reliable)
        if fetch_image_pixabay(kw, out_path):
            print(f"   Downloaded from Pixabay: {out_path.name}")
            success = True
        
        # Try Pexels as backup
        elif fetch_image_pexels(kw, out_path):
            print(f"   Downloaded from Pexels: {out_path.name}")
            success = True
        
        # Try Unsplash
        elif fetch_image_unsplash(kw, out_path):
            print(f"   Downloaded from Unsplash: {out_path.name}")
            success = True        # Try Pexels first
        success = fetch_image_pexels(kw, IMG_DIR / f"img_{img_index:02d}.jpg")
        
        if not success:
            # Try Unsplash
            print(f"   Trying Unsplash...")
            success = fetch_image_unsplash(kw, IMG_DIR / f"img_{img_index:02d}.jpg")
        
        if not success:
            # Try fallback keyword on Unsplash
            fallback = random.choice(FALLBACKS)
            print(f"   Fallback: '{fallback}'")
            success = fetch_image_unsplash(fallback, IMG_DIR / f"img_{img_index:02d}.jpg")
        
        if not success:
            # Last resort: Picsum with unique seed
            print(f"   Using Picsum random image")
            success = fetch_image_picsum(IMG_DIR / f"img_{img_index:02d}.jpg", seed_base + img_index)
        
        if success:
            print(f"   Downloaded img_{img_index:02d}.jpg")
            img_index += 1
        else:
            print(f"   Failed to download image")
        
        time.sleep(0.5)  # Rate limiting
    
    # Fill remaining slots with Picsum
    while img_index <= max_images:
        print(f"\n Filling slot {img_index} with Picsum")
        success = fetch_image_picsum(IMG_DIR / f"img_{img_index:02d}.jpg", seed_base + img_index * 100)
        if success:
            print(f"   Downloaded img_{img_index:02d}.jpg")
        img_index += 1
        time.sleep(0.3)

    print(f"\n Downloaded {img_index-1} images to images/")

if __name__ == "__main__":
    main()


