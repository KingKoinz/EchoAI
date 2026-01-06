import yaml
import requests
from pathlib import Path

# -----------------------------
# Paths
# -----------------------------
BASE_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = BASE_DIR / "config" / "settings.yaml"
TOPICS_PATH = BASE_DIR / "input" / "topics.txt"
OUTPUT_DIR = BASE_DIR / "output"

OUTPUT_DIR.mkdir(exist_ok=True)

# -----------------------------
# Load config
# -----------------------------
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

API_KEY = config["claude"]["api_key"]
MODEL = config["claude"]["model"]

# -----------------------------
# Claude API call (CURRENT FORMAT)
# -----------------------------
def call_claude(prompt: str) -> str:
    url = "https://api.anthropic.com/v1/messages"

    headers = {
        "x-api-key": API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    payload = {
        "model": MODEL,
        "max_tokens": 400,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    response = requests.post(url, headers=headers, json=payload, timeout=60)

    # Helpful debug if it fails again
    if response.status_code != 200:
        print("STATUS:", response.status_code)
        print("RESPONSE:", response.text)

    response.raise_for_status()

    data = response.json()
    return data["content"][0]["text"]

# -----------------------------
# Main logic
# -----------------------------
def main():
    if not TOPICS_PATH.exists():
        raise FileNotFoundError("topics.txt not found")

    topics = [t.strip() for t in TOPICS_PATH.read_text(encoding="utf-8").splitlines() if t.strip()]
    if not topics:
        raise ValueError("topics.txt is empty")

    topic = topics[0]

    prompt = f"""
Write a TikTok script that lasts about 2030 seconds.

Topic:
{topic}

Rules:
- First sentence must hook attention immediately
- Conversational, spoken language
- Short sentences
- Simple words
- No emojis
- No stage directions
- End with a subtle call to action
- Output ONLY the spoken script
"""

    print(" Generating script with Claude...")
    script = call_claude(prompt)

    out_file = OUTPUT_DIR / "script.txt"
    out_file.write_text(script, encoding="utf-8")

    print("\n SCRIPT GENERATED:\n")
    print(script)
    print(f"\n Saved to: {out_file}")

# -----------------------------
if __name__ == "__main__":
    main()
