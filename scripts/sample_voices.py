import pyttsx3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
SAMPLES_DIR = BASE_DIR / "temp" / "voice_samples"
SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

# Sample text for testing
SAMPLE_TEXT = "Hey there! This is a sample voice for your TikTok videos. Does this sound good?"

def main():
    print(" Sampling all available voices...\n")
    
    engine = pyttsx3.init()
    voices = engine.getProperty("voices")
    
    print(f"Found {len(voices)} voices:\n")
    
    for i, voice in enumerate(voices, 1):
        print(f"{i}. {voice.name}")
        print(f"   ID: {voice.id}")
        print(f"   Languages: {voice.languages}")
        
        # Generate sample
        output_file = SAMPLES_DIR / f"voice_{i:02d}_{voice.name.replace(' ', '_')}.wav"
        
        engine.setProperty("voice", voice.id)
        engine.setProperty("rate", 140)  # Same rate as your main script
        engine.save_to_file(SAMPLE_TEXT, str(output_file))
        engine.runAndWait()
        
        print(f"    Sample saved: {output_file.name}\n")
    
    print(f"\n All samples saved to: {SAMPLES_DIR}")
    print("\n Listen to the samples and note the voice number you like!")
    print("   Then update make_voice.py with that voice ID.")

if __name__ == "__main__":
    main()
