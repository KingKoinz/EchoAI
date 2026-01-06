import sys
import re
from pathlib import Path
import yaml
import anthropic

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG = BASE_DIR / "config" / "settings.yaml"
OUTPUT_DIR = BASE_DIR / "output"
SCRIPT_OUT = OUTPUT_DIR / "script.txt"


def load_config():
    # Check for job-specific config first
    job_config = OUTPUT_DIR / "settings.yaml"
    config_path = job_config if job_config.exists() else CONFIG
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def strip_emojis(text: str) -> str:
    # Removes all emoji / non-BMP unicode characters
    return re.sub(r"[\U00010000-\U0010FFFF]", "", text)

def uncensor_script(script: str, original_topic: str) -> str:
    """Aggressively restore ANY censored profanity patterns"""
    
    # Extract all curse words from the original topic
    curse_words = re.findall(
        r'\b(fuck|fucking|fucked|fucker|shit|shitty|shitting|ass|asshole|damn|damned|bitch|bitching|bitches|cock|piss|pissed|pissing|hell|crap|bastard|bullshit)\b',
        original_topic.lower()
    )
    
    if not curse_words:
        return script
    
    # Build aggressive replacement patterns for each detected curse
    uncensored = script
    for curse in set(curse_words):
        # Match any censorship pattern: f***, f**k, f*ck, [profanity], ***
        # Replace with the actual word from the topic
        patterns = [
            r'\*+',  # Any string of asterisks
            r'\[profanity\]',
            r'\[curse\]',
            r'\[explicit\]',
            r'\[redacted\]',
            curse[0] + r'\*+' + curse[-1],  # f***k pattern
            curse[0] + r'\*+',  # f*** pattern
        ]
        
        for pattern in patterns:
            # Try to match context around censored word
            uncensored = re.sub(pattern, curse, uncensored, flags=re.IGNORECASE)
    
    return uncensored


def get_style_prompt(style: str, topic: str, duration: int) -> str:
    """Return appropriate prompt based on video style"""
    
    prompts = {
        "viral_facts": f"""You're a viral TikTok creator making a {duration}-second video about: {topic}

VIBE CHECK:
- Talk like you're texting your best friend, not writing an essay
- Use "like", "literally", "honestly", "not gonna lie" naturally
- Add dramatic pauses with "..." 
- Be self-aware and slightly chaotic
- Make people go "that's so real though"

STRUCTURE (roughly {duration * 3} words total):
- Hook in first 2 seconds - make them STOP scrolling
- VARY YOUR HOOKS: "Okay but", "Nobody talks about", "Tell me why", "So apparently", "Here's the thing", "You ever notice", "Fun fact", or jump straight into a shocking statement
- Build tension or relatability 
- Add a surprising twist, hot take, or punchline
- End with something that makes them want to comment

ENERGY:
- Conversational, NOT scripted
- Use sentence fragments. Like this.
- Add personality quirks (exaggeration, self-deprecating humor, random tangents)
- Sound like someone who's chronically online
- DON'T always start with "Wait" - mix up your openings

FORMAT: 5-6 short paragraphs in quotes
NO emojis, NO hashtags, text only

Write ONLY the script - straight fire, no explanations.""",

        "story_time": f"""You're a storyteller creating a {duration}-second narrative video about: {topic}

STORYTELLING APPROACH:
- Set the scene immediately - paint a vivid picture
- VARY YOUR OPENINGS: "So this one time", "Let me tell you about", "Picture this", "I'll never forget when", "There was this moment", "You know what's crazy", "Story time", or jump straight into the scene
- Build a clear narrative arc: setup → conflict/tension → resolution
- Add dramatic pauses and pacing with "..."
- Make it feel personal and relatable
- DON'T always use "So..." - mix up your story intros

STRUCTURE (roughly {duration * 3} words total):
- Opening: Hook with an intriguing setup ("So this one time...", "You won't believe what happened...")
- Middle: Build tension, add details, create suspense
- Climax: The moment everything changes or the key revelation
- Ending: Satisfying conclusion or cliffhanger that makes them think

TONE:
- Warm and conversational, like telling a friend
- Descriptive but not overly formal
- Emotional beats - make them feel something
- Natural pacing with dramatic emphasis

FORMAT: 5-6 short paragraphs in quotes
NO emojis, NO hashtags, text only

Write ONLY the script - pure storytelling.""",

        "motivational": f"""You're a motivational speaker creating a {duration}-second empowering video about: {topic}

MOTIVATION STYLE:
- Start with power - grab attention with a bold statement
- VARY YOUR OPENINGS: "Listen", "Real talk", "Here's the truth", "Stop", "You already know", "Let's be honest", "I'm gonna say it", "The thing is", or lead with a powerful declaration
- Be direct, confident, and unapologetically inspiring
- Challenge limiting beliefs and spark action
- End with a clear call-to-action or empowering message
- DON'T always start with "Listen" - command attention in different ways

STRUCTURE (roughly {duration * 3} words total):
- Hook: Bold opening that demands attention ("Stop making excuses...", "You already know...")
- Build: Layer in truth bombs, reframe mindset, challenge the status quo
- Climax: The core empowering message - the "aha" moment
- Close: Clear takeaway or call-to-action ("So start today", "You've got this")

ENERGY:
- Confident and direct, not preachy
- Use powerful, action-oriented language
- Short punchy sentences for impact
- Authentic and real, not corporate motivation

FORMAT: 5-6 short paragraphs in quotes
NO emojis, NO hashtags, text only

Write ONLY the script - pure motivation.""",

        "educational": f"""You're an educator creating a {duration}-second informative video about: {topic}

TEACHING APPROACH:
- Start with a clear promise of what they'll learn
- VARY YOUR OPENINGS: "Here's what you need to know", "Let me break this down", "Quick lesson", "Three things about", "The science behind", "Ever wondered why", "I'm gonna explain", or lead with an intriguing question
- Organize information logically - make it easy to follow
- Explain clearly without dumbing down or overcomplicating
- End with a key takeaway or practical application
- DON'T always use the same intro phrase - grab attention in fresh ways

STRUCTURE (roughly {duration * 3} words total):
- Hook: Tell them what they'll learn ("3 things about...", "The truth about...")
- Explanation: Break down concepts step-by-step or point-by-point
- Examples/Details: Make it concrete and understandable
- Summary: Reinforce the key lesson or actionable insight

CLARITY:
- Use simple, precise language
- Number your points if covering multiple items (First... Second... Finally...)
- Define terms if needed, but keep it accessible
- Authoritative but not condescending

FORMAT: 5-6 short paragraphs in quotes
NO emojis, NO hashtags, text only

Write ONLY the script - clear and informative."""
    }
    
    # Default to viral_facts if style not found
    return prompts.get(style, prompts["viral_facts"])


def generate_script(topic: str, api_key: str, model: str, duration: int, style: str = "viral_facts"):
    client = anthropic.Anthropic(api_key=api_key)

    prompt = get_style_prompt(style, topic, duration)
    
    message = client.messages.create(
        model=model,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )

    # Strip emojis
    clean_text = strip_emojis(message.content[0].text)
    
    # Restore any censored profanity from original topic
    uncensored_text = uncensor_script(clean_text, topic)
    
    return uncensored_text.strip()


def main():
    if len(sys.argv) < 2:
        print("Usage: python make_script.py <topic>")
        sys.exit(1)

    topic = " ".join(sys.argv[1:])
    print(f"Generating script for: {topic}")

    config = load_config()
    api_key = config["claude"]["api_key"]
    model = config["claude"]["model"]
    duration = config["video"]["duration_seconds"]
    style = config["video"].get("style", "viral_facts")
    
    print(f"Style: {style}")

    script = generate_script(topic, api_key, model, duration, style)

    OUTPUT_DIR.mkdir(exist_ok=True)
    SCRIPT_OUT.write_text(script, encoding="utf-8")

    print(f"Script saved to: {SCRIPT_OUT}")


if __name__ == "__main__":
    main()

