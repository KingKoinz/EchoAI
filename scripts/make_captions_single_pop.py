from pathlib import Path
import os
import whisper

os.environ["PATH"] += os.pathsep + r"C:\Users\Walt\Downloads\ffmpeg\ffmpeg-master-latest-win64-gpl\bin"

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"

AUDIO = OUTPUT_DIR / "voice.wav"
ASS_OUT = OUTPUT_DIR / "captions.ass"

def sec_to_ass(t: float) -> str:
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    cs = int((t - int(t)) * 100)
    return f"{h}:{m:02}:{s:02}.{cs:02}"

def main():
    print(" Generating single word pop captions...")

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
        # Large white text with black outline, centered, bold
        "Style: Default,Arial Black,88,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,"
        "1,0,0,0,100,100,0,0,1,4,0,2,50,50,180,1",
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

    for word_data in all_words:
        start_time = word_data["start"]
        end_time = word_data["end"]
        word = word_data["text"]
        
        start_ass = sec_to_ass(start_time)
        end_ass = sec_to_ass(end_time)
        
        # Add scale animation: starts at 80%, bounces to 120%, settles at 100%
        duration_ms = int((end_time - start_time) * 1000)
        bounce_time = min(200, duration_ms // 3)
        
        # Animation: \t(0,200,\fscx120\fscy120) - scale up in first 200ms
        # Then scale back to 100% for remainder
        animation = f"{{\\t(0,{bounce_time},\\fscx120\\fscy120)\\t({bounce_time},{duration_ms},\\fscx100\\fscy100)}}"
        
        ass_lines.append(
            f"Dialogue: 0,{start_ass},{end_ass},Default,,0,0,0,,{animation}{word}"
        )

    ASS_OUT.write_text("\n".join(ass_lines), encoding="utf-8")
    print(f" Single word pop captions written to: {ASS_OUT}")

if __name__ == "__main__":
    main()
