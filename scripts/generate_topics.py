from anthropic import Anthropic
from pathlib import Path
import random

BASE_DIR = Path(__file__).resolve().parents[1]
CONFIG = BASE_DIR / "config" / "settings.yaml"

# Load API key
import yaml
with open(CONFIG) as f:
    config = yaml.safe_load(f)
    API_KEY = config["claude"]["api_key"]

client = Anthropic(api_key=API_KEY)

TOPIC_PROMPTS = [
    "Generate 5 viral TikTok video topic ideas about everyday relatable situations that would get millions of views.",
    "Generate 5 controversial but engaging TikTok topics about dating, relationships, and modern life.",
    "Generate 5 funny TikTok video ideas about social media trends and online behavior.",
    "Generate 5 TikTok topics about weird habits people have but don't talk about.",
    "Generate 5 viral TikTok ideas about Gen Z vs Millennials differences.",
    "Generate 5 TikTok topics exposing common scams or red flags people should know.",
    "Generate 5 story-time TikTok ideas about creepy or mysterious experiences.",
    "Generate 5 hot take TikTok topics that will spark debate in the comments.",
]

def generate_topics(count=10):
    """Generate trending TikTok topic ideas"""
    
    prompt_choice = random.choice(TOPIC_PROMPTS)
    
    print(f" Generating {count} trending TikTok topic ideas...\n")
    
    response = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=1000,
        messages=[{
            "role": "user",
            "content": f"{prompt_choice}\n\nList them as numbered items (1-5). Make them catchy, viral-worthy, and perfect for short-form content. Each topic should be 5-15 words."
        }]
    )
    
    topics_text = response.content[0].text
    
    # Parse topics from response
    topics = []
    for line in topics_text.split('\n'):
        line = line.strip()
        # Match lines like "1. Topic" or "1) Topic"
        if line and any(line.startswith(f"{i}.") or line.startswith(f"{i})") for i in range(1, 10)):
            # Remove number prefix
            topic = line.split('.', 1)[-1].split(')', 1)[-1].strip()
            if topic and len(topic) > 10:  # Make sure it's substantial
                topics.append(topic)
    
    return topics

def main():
    print("=" * 60)
    print(" TIKTOK TOPIC GENERATOR")
    print("=" * 60)
    
    topics = generate_topics()
    
    if not topics:
        print(" Failed to generate topics. Please try again.")
        return None
    
    print("\n Generated Topics:\n")
    for i, topic in enumerate(topics, 1):
        print(f"  {i}. {topic}")
    
    print("\n" + "=" * 60)
    print(" Pick a number (1-5) or press Enter for random")
    print("=" * 60)
    
    try:
        choice = input("\nYour choice: ").strip()
        
        if not choice:
            # Random selection
            selected = random.choice(topics)
            print(f"\n Randomly selected: {selected}")
        else:
            idx = int(choice) - 1
            if 0 <= idx < len(topics):
                selected = topics[idx]
                print(f"\n Selected: {selected}")
            else:
                print(f"\n Invalid choice. Using first topic.")
                selected = topics[0]
        
        return selected
        
    except (ValueError, KeyboardInterrupt):
        print(f"\n  Using first topic: {topics[0]}")
        return topics[0]

if __name__ == "__main__":
    topic = main()
    if topic:
        print(f"\n Ready to generate video for: {topic}")
        print("\n Run: python run_pipeline.py \"{topic}\"")
