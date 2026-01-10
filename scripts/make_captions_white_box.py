from pathlib import Path
import os
import re
import whisper

os.environ["PATH"] += os.pathsep + r"C:\Users\Walt\Downloads\ffmpeg\ffmpeg-master-latest-win64-gpl\bin"

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"

AUDIO = OUTPUT_DIR / "voice.wav"
ASS_OUT = OUTPUT_DIR / "captions.ass"

WORDS_PER_PHRASE = 4
FONT = "Arial Black"
FONTSIZE = 68

def sec_to_ass(t: float) -> str:
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    cs = int((t - int(t)) * 100)
    return f"{h}:{m:02}:{s:02}.{cs:02}"

def is_sentence_end(word: str) -> bool:
    return bool(re.search(r"[.!?]$", word.strip()))

def main():
    print(" Generating white box captions (3-4 words)...")

    if not AUDIO.exists():
        raise FileNotFoundError("voice.wav not found")

    model = whisper.load_model("base")
    result = model.transcribe(str(AUDIO), word_timestamps=True)

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
        # White background box with black text, centered
        "Style: Default,Arial Black,68,&H00000000,&H000000FF,&H00000000,&H00FFFFFF,"
        "1,0,0,0,100,100,0,0,3,0,0,2,50,50,180,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

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

    word_buffer = []
    
    for i, current_word in enumerate(all_words):
        word_buffer.append(current_word)
        
        if len(word_buffer) > WORDS_PER_PHRASE:
            word_buffer.pop(0)
        
        is_last = (i == len(all_words) - 1)
        ends_sentence = is_sentence_end(current_word["text"])
        
        if len(word_buffer) == WORDS_PER_PHRASE or is_last or ends_sentence:
            start_time = word_buffer[0]["start"]
            end_time = current_word["end"]
            
            phrase = " ".join(w["text"] for w in word_buffer)
            phrase_with_padding = f"  {phrase}  "
            
            start_ass = sec_to_ass(start_time)
            end_ass = sec_to_ass(end_time)
            
            ass_lines.append(
                f"Dialogue: 0,{start_ass},{end_ass},Default,,0,0,0,,{phrase_with_padding}"
            )
            
            if ends_sentence and not is_last:
                word_buffer.clear()

    ASS_OUT.write_text("\n".join(ass_lines), encoding="utf-8")
    print(f" White box captions written to: {ASS_OUT}")

if __name__ == "__main__":
    main()
