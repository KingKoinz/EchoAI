from pathlib import Path
import os
import whisper
import re

# Ensure ffmpeg is visible to Whisper
os.environ["PATH"] += os.pathsep + r"C:\Users\Walt\Downloads\ffmpeg\ffmpeg-master-latest-win64-gpl\bin"

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"

AUDIO = OUTPUT_DIR / "voice.wav"
ASS_OUT = OUTPUT_DIR / "captions.ass"

MAX_WORDS_VISIBLE = 2  # Show previous and current word only


def sec_to_ass(t: float) -> str:
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    cs = int((t - int(t)) * 100)
    return f"{h}:{m:02}:{s:02}.{cs:02}"


def is_sentence_end(word: str) -> bool:
    """Check if word ends with sentence punctuation"""
    return bool(re.search(r'[.!?]$', word.strip()))


def main():
    print(" Generating TikTok-style bouncing captions with word highlighting...")

    if not AUDIO.exists():
        raise FileNotFoundError("voice.wav not found")

    model = whisper.load_model("base")
    result = model.transcribe(
        str(AUDIO),
        word_timestamps=True
    )

    ass_lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1080",
        "PlayResY: 1920",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding",
        # Bottom-center, TikTok safe margins, white text with black outline
        "Style: Default,Arial Black,68,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,"
        "1,0,0,0,100,100,0,0,1,3,0,2,50,50,180,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    # Collect all words
    all_words = []
    for seg in result.get("segments", []):
        for w in seg.get("words", []):
            word_text = w.get("word", "").strip()
            if word_text:
                all_words.append({
                    "text": word_text,
                    "start": w.get("start"),
                    "end": w.get("end")
                })

    # Create captions with word buffer (shows multiple words)
    word_buffer = []
    captions = []
    
    for i, current_word in enumerate(all_words):
        word_buffer.append(current_word)
        
        if len(word_buffer) > MAX_WORDS_VISIBLE:
            word_buffer.pop(0)
        
        # First line: previous word(s) (white, no bounce)
        prev_text = " ".join([w["text"] for w in word_buffer[:-1]]) if len(word_buffer) > 1 else ""
        # Second line: current word (yellow, bounce)
        curr_word = word_buffer[-1]["text"]
        curr_bounce = r"{\c&H00FFFF&}{\t(0,100,\fscx115\fscy115)}{\t(100,200,\fscx100\fscy100)}" + curr_word + r"{\c&HFFFFFF&}"

        start_time = word_buffer[0]["start"]
        if i < len(all_words) - 1:
            next_word_start = all_words[i + 1]["start"]
            extended_end = min(current_word["end"] + 0.5, next_word_start)
            end_time = extended_end
        else:
            # Last word - extend duration
            end_time = current_word["end"] + 1.0

        # Add stacked lines with different vertical margins
        if prev_text:
            captions.append({
                "start": start_time,
                "end": end_time,
                "text": prev_text,
                "margin_v": 220  # Higher up
            })
        captions.append({
            "start": start_time,
            "end": end_time,
            "text": curr_bounce,
            "margin_v": 180  # Lower, closer to bottom
        })

        if is_sentence_end(current_word["text"]):
            word_buffer.clear()
    
    # Now create ASS dialogues from the captions
    for caption in captions:
        start = sec_to_ass(caption["start"])
        end = sec_to_ass(caption["end"])
        margin_v = caption.get("margin_v", 180)
        ass_lines.append(
            f"Dialogue: 0,{start},{end},Default,,0,0,{margin_v},,{caption['text']}"
        )

    ASS_OUT.write_text("\n".join(ass_lines), encoding="utf-8")
    print(f" TikTok-style bouncing captions written to: {ASS_OUT}")
    print(f"   - Shows {MAX_WORDS_VISIBLE} words at a time")
    print(f"   - Current word highlighted in yellow with bounce effect")


if __name__ == "__main__":
    main()
