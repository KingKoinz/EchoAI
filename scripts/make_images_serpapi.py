#!/usr/bin/env python3
"""
Generate and download images using SerpAPI Google Images API
Downloads 6 portrait images based on keywords from the generated script
"""

import os
import sys
import yaml
import requests
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def load_config():
    """Load configuration from settings.yaml"""
    config_path = project_root / "config" / "settings.yaml"
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def fetch_images_serpapi(query, api_key, num_images=6):
    """
    Fetch images from Google Images using SerpAPI
    
    Args:
        query: Search query string
        api_key: SerpAPI API key
        num_images: Number of images to fetch (default 6)
    
    Returns:
        List of image URLs
    """
    print(f" Searching Google Images for: {query}")
    
    # SerpAPI parameters for Google Images
    params = {
        "engine": "google_images",
        "q": query,
        "api_key": api_key,
        "ijn": "0",  # First page
        "imgsz": "l",  # Large images
        "hl": "en",
        "gl": "us"
    }
    
    try:
        response = requests.get("https://serpapi.com/search.json", params=params)
        response.raise_for_status()
        data = response.json()
        
        # Extract image URLs from results
        images_results = data.get("images_results", [])
        image_urls = []
        
        for img in images_results:
            # Try to get the original high-res image URL
            original_url = img.get("original")
            if original_url and not original_url.startswith("x-raw-image://"):
                image_urls.append(original_url)
                if len(image_urls) >= num_images:
                    break
        
        print(f" Found {len(image_urls)} images")
        return image_urls
    
    except Exception as e:
        print(f" Error fetching images from SerpAPI: {e}")
        return []


def download_image(url, save_path):
    """
    Download an image from URL to save_path
    
    Args:
        url: Image URL
        save_path: Path to save the image
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Custom headers to avoid blocking
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, stream=True, timeout=10)
        response.raise_for_status()
        
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return True
    
    except Exception as e:
        print(f"  Failed to download {url}: {e}")
        return False


def extract_keywords_from_script(script_path):
    """
    Extract keywords from the generated script
    Simple extraction: take first meaningful sentence
    
    Args:
        script_path: Path to script.txt
    
    Returns:
        str: Search query string
    """
    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            script = f.read()
        
        # Take first 100 characters and clean up
        lines = script.split('\n')
        first_meaningful = ""
        
        for line in lines:
            line = line.strip()
            if len(line) > 20:  # Skip very short lines
                first_meaningful = line
                break
        
        # Extract topic from first sentence (simple approach)
        if first_meaningful:
            # Remove common filler words
            query = first_meaningful.replace("Wait, you guys have never heard", "")
            query = query.replace("Let me break it down for you.", "")
            query = query.strip().rstrip('?!.,')
            
            # Take first 50 chars for search
            query = ' '.join(query.split()[:8])
            return query if query else "trending topic"
        
        return "trending topic"
    
    except Exception as e:
        print(f"  Error reading script: {e}")
        return "trending topic"


def main():
    print("\n" + "="*50)
    print("  DOWNLOADING IMAGES FROM GOOGLE (SerpAPI)")
    print("="*50 + "\n")
    
    # Load config
    config = load_config()
    serpapi_key = config.get('serpapi', {}).get('api_key', '')
    
    if not serpapi_key:
        print(" ERROR: SerpAPI key not found in settings.yaml")
        print("   Please add your SerpAPI key to config/settings.yaml:")
        print("   serpapi:")
        print("     api_key: 'YOUR_KEY_HERE'")
        print("\n   Get your key at: https://serpapi.com/")
        sys.exit(1)
    
    # Paths
    script_path = project_root / "output" / "script.txt"
    images_dir = project_root / "images"
    
    # Check if script exists
    if not script_path.exists():
        print(f" ERROR: Script file not found at {script_path}")
        print("   Please run scripts/make_script.py first")
        sys.exit(1)
    
    # Create images directory
    images_dir.mkdir(exist_ok=True)
    print(f" Images directory: {images_dir}\n")
    
    # Extract keywords from script
    query = extract_keywords_from_script(script_path)
    print(f" Search keywords: {query}\n")
    
    # Fetch image URLs from SerpAPI
    image_urls = fetch_images_serpapi(query, serpapi_key, num_images=6)
    
    if not image_urls:
        print(" No images found. Using fallback search...")
        image_urls = fetch_images_serpapi("trending viral content", serpapi_key, num_images=6)
    
    if not image_urls:
        print(" Failed to fetch any images from SerpAPI")
        sys.exit(1)
    
    # Download images
    print(f"\n Downloading {len(image_urls)} images...\n")
    
    downloaded_count = 0
    for i, url in enumerate(image_urls, 1):
        output_path = images_dir / f"image_{i:02d}.jpg"
        print(f"  [{i}/{len(image_urls)}] Downloading image {i}...")
        
        if download_image(url, output_path):
            file_size = output_path.stat().st_size / 1024  # KB
            print(f"       Saved to {output_path.name} ({file_size:.1f} KB)")
            downloaded_count += 1
        else:
            print(f"       Failed to download")
    
    print(f"\n{'='*50}")
    print(f" Downloaded {downloaded_count}/{len(image_urls)} images successfully")
    print(f" Location: {images_dir}")
    print("="*50 + "\n")


if __name__ == "__main__":
    main()
