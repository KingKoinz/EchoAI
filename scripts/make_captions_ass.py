from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"

SRT_PATH = OUTPUT_DIR / "captions.srt"
ASS_PATH = OUTPUT_DIR / "captions.ass"

ASS_HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,56,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,3,0,2,120,120,260,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

def srt_time_to_ass(t):
    # 00:00:39,160  0:00:39.16
    h, m, rest = t.split(":")
    s, ms = rest.split(",")
    return f"{int(h)}:{m}:{s}.{ms[:2]}"

def main():
    if not SRT_PATH.exists():
        raise FileNotFoundError("captions.srt not found")

    lines = SRT_PATH.read_text(encoding="utf-8").splitlines()
    ass_lines = [ASS_HEADER]

    i = 0
    while i < len(lines):
        if "-->" in lines[i]:
            start, end = lines[i].split(" --> ")
            text = lines[i + 1].strip().replace("\n", " ")

            ass_lines.append(
                f"Dialogue: 0,{srt_time_to_ass(start)},{srt_time_to_ass(end)},Default,,0,0,0,,{text}"
            )
            i += 3
        else:
            i += 1

    ASS_PATH.write_text("\n".join(ass_lines), encoding="utf-8")
    print(f" ASS captions created: {ASS_PATH}")

if __name__ == "__main__":
    main()
