from pathlib import Path
import whisper

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"

AUDIO = OUTPUT_DIR / "voice.wav"
ASS_OUT = OUTPUT_DIR / "captions.ass"

def sec_to_ass(t):
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    cs = int((t - int(t)) * 100)
    return f"{h}:{m:02}:{s:02}.{cs:02}"

def main():
    print(" Transcribing with word timing (karaoke mode)...")

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
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Default,Arial,58,&H00FFFFFF,&H0000FFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,3,0,2,120,120,260,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
    ]

    for seg in result["segments"]:
        if "words" not in seg:
            continue

        start = sec_to_ass(seg["start"])
        end = sec_to_ass(seg["end"])

        karaoke = ""
        for w in seg["words"]:
            dur = int((w["end"] - w["start"]) * 100)
            karaoke += f"{{\\k{dur}}}{w['word']} "

        ass_lines.append(
            f"Dialogue: 0,{start},{end},Default,,0,0,0,,{karaoke.strip()}"
        )

    ASS_OUT.write_text("\n".join(ass_lines), encoding="utf-8")
    print(f" Karaoke captions written to: {ASS_OUT}")

if __name__ == "__main__":
    main()
