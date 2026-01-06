"""Download 6 stock images from Picsum (no API needed)"""
import requests
from pathlib import Path

IMG_DIR = Path(__file__).resolve().parent / "images"
IMG_DIR.mkdir(exist_ok=True)

# Use different seeds for variety
seeds = ["trump1", "trump2", "leader", "power", "boss", "success"]

for i, seed in enumerate(seeds, 1):
    url = f"https://picsum.photos/seed/{seed}/1080/1920"
    print(f"Downloading image {i}/6 ({seed})...")
    
    try:
        r = requests.get(url, timeout=15)
        if r.status_code == 200 and len(r.content) > 10000:
            out_path = IMG_DIR / f"img_{i:02d}.jpg"
            out_path.write_bytes(r.content)
            size_kb = len(r.content) / 1024
            print(f"  ✅ {size_kb:.1f}KB saved to {out_path.name}")
        else:
            print(f"  ❌ Failed (status={r.status_code}, size={len(r.content)})")
    except Exception as e:
        print(f"  ❌ Error: {e}")

print("\n✅ Downloaded 6 images to images/")
