"""
FREE Alternative: Use OpenAI's GPT-3.5 (free tier) or local models
"""
import sys
from pathlib import Path
import requests

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"
SCRIPT_OUT = OUTPUT_DIR / "script.txt"

def generate_script_free(topic: str, duration: int = 25):
    """
    FREE OPTION 1: Use GPT4All (completely free, runs locally)
    Install: pip install gpt4all
    
    FREE OPTION 2: Use Hugging Face API (free tier)
    Get key from: https://huggingface.co/settings/tokens
    """
    
    # Option 1: GPT4All (Local, Free, No API key needed)
    try:
        from gpt4all import GPT4All
        model = GPT4All("orca-mini-3b-gguf2-q4_0.gguf")  # 2GB download first time
        
        prompt = f"""Write a viral {duration}-second TikTok script about: {topic}

Make it:
- Conversational and engaging
- Start with a hook
- {duration * 3} words total
- No emojis, just text

Script:"""
        
        response = model.generate(prompt, max_tokens=200)
        return response.strip()
        
    except ImportError:
        pass
    
    # Option 2: Hugging Face Inference API (Free tier: 1000 requests/day)
    try:
        HF_API_KEY = "YOUR_HF_TOKEN"  # Get from huggingface.co/settings/tokens
        
        if HF_API_KEY and HF_API_KEY != "YOUR_HF_TOKEN":
            headers = {"Authorization": f"Bearer {HF_API_KEY}"}
            
            API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.1"
            
            prompt = f"Write a {duration}s viral TikTok script about: {topic}. Make it engaging, {duration*3} words."
            
            response = requests.post(
                API_URL,
                headers=headers,
                json={"inputs": prompt, "parameters": {"max_new_tokens": 200}}
            )
            
            if response.status_code == 200:
                return response.json()[0]["generated_text"].strip()
    except:
        pass
    
    # Option 3: Template-based (No AI needed!)
    templates = {
        "facts": f"Wait, you need to hear this about {topic}.\n\nSo basically...\n\n[Main point]\n\nHonestly, that's wild.\n\nLike, think about it...\n\n[Conclusion]\n\nComment if you knew this!",
        "story": f"Okay so this happened with {topic}.\n\nI was literally...\n\n[Story part 1]\n\nAnd then...\n\n[Story part 2]\n\nNot gonna lie, I couldn't believe it.",
    }
    
    return templates["facts"].replace("[Main point]", f"Something about {topic}").replace("[Conclusion]", "Mind blown!")

def main():
    if len(sys.argv) < 2:
        print(" Usage: python make_script_free.py <topic>")
        sys.exit(1)
    
    topic = " ".join(sys.argv[1:])
    print(f" Generating FREE script for: {topic}")
    
    script = generate_script_free(topic)
    
    OUTPUT_DIR.mkdir(exist_ok=True)
    SCRIPT_OUT.write_text(script, encoding="utf-8")
    
    print(f" Script saved (100% FREE!)")
    print(f"\n{script}")

if __name__ == "__main__":
    main()
