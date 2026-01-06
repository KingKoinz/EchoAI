from pathlib import Path
import os
import re
import whisper

# Ensure ffmpeg is visible to Whisper (used internally by whisper)
os.environ["PATH"] += os.pathsep + r"C:\Users\Walt\Downloads\ffmpeg\ffmpeg-master-latest-win64-gpl\bin"

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"

AUDIO = OUTPUT_DIR / "voice.wav"
ASS_OUT = OUTPUT_DIR / "captions.ass"

# ---- STYLE YOU WANT (crime/news tiles) ----
WORDS_PER_PHRASE = 4        # exactly like your screenshot vibe (2x2 grid)
FONT = "Arial Black"
FONTSIZE = 64

# Position of the 2-line tile block (centered, TikTok-safe)
CENTER_X = 540
TOP_ROW_Y = 1550  # Much lower on screen
BOTTOM_ROW_Y = 1680  # Much lower on screen

# Spacing between word tiles in a row (negative = overlap)
GAP_X = -5

# Add padding inside each colored box (cheap + effective)
# (extra spaces = bigger box)
PAD_LEFT = " "
PAD_RIGHT = " "

# Style names that correspond to the colored styles we defined
STYLE_NAMES = ["Orange", "Pink", "Yellow", "Green"]


def sec_to_ass(t: float) -> str:
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    cs = int((t - int(t)) * 100)
    return f"{h}:{m:02}:{s:02}.{cs:02}"


def is_sentence_end(word: str) -> bool:
    """Check if word ends with sentence punctuation"""
    return bool(re.search(r"[.!?]$", word.strip()))


def safe_word(w: str) -> str:
    # strip weird quotes, keep punctuation at end
    w = w.strip()
    w = w.replace("\n", " ")
    return w


def approx_text_width_px(text: str) -> int:
    """
    We need width to center tiles. For simplicity (and reliability),
    approximate width using character count. Arial Black ~0.62 * fontsize per char.
    This avoids Pillow/font issues.
    """
    return int(len(text) * (FONTSIZE * 0.62))


def make_tile_dialogue(start_s: float, end_s: float, x: int, y: int, word: str, style_name: str) -> str:
    start = sec_to_ass(start_s)
    end = sec_to_ass(end_s)

    # Use specific style with its own BackColour defined in style header
    # \an5 centers at pos(x,y)
    # Add spaces around the word to create padding in the box
    tile_text = f"{PAD_LEFT}{word}{PAD_RIGHT}"

    overrides = (
        r"{\an5"
        + rf"\pos({x},{y})"
        + r"}"
    )

    return f"Dialogue: 0,{start},{end},{style_name},,0,0,0,,{overrides}{tile_text}"


def main():
    print(" Generating COLOR-BOX word tiles (like crime/news TikTok)...")

    if not AUDIO.exists():
        raise FileNotFoundError("voice.wav not found in output/")

    model = whisper.load_model("base")
    result = model.transcribe(str(AUDIO), word_timestamps=True)

    # ---- ASS HEADER ----
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
        # Create 4 separate styles, each with its own BackColour
        # BorderStyle=4 creates opaque shadow box (background)
        # Black text on colored backgrounds for better contrast
        f"Style: Orange,{FONT},{FONTSIZE},&H00000000&,&H000000FF&,&H00000000&,&H0000A5FF&,"
        "1,0,0,0,100,100,0,0,4,0,2,2,0,0,0,1",
        f"Style: Pink,{FONT},{FONTSIZE},&H00000000&,&H000000FF&,&H00000000&,&HFF1493FF&,"
        "1,0,0,0,100,100,0,0,4,0,2,2,0,0,0,1",
        f"Style: Yellow,{FONT},{FONTSIZE},&H00000000&,&H000000FF&,&H00000000&,&H0000FFFF&,"
        "1,0,0,0,100,100,0,0,4,0,2,2,0,0,0,1",
        f"Style: Green,{FONT},{FONTSIZE},&H00000000&,&H000000FF&,&H00000000&,&H0000FF00&,"
        "1,0,0,0,100,100,0,0,4,0,2,2,0,0,0,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    # ---- COLLECT WORDS ----
    words = []
    for seg in result.get("segments", []):
        for w in seg.get("words", []):
            txt = safe_word(w.get("word", ""))
            if txt:
                words.append({"text": txt, "start": w["start"], "end": w["end"]})

    if not words:
        raise RuntimeError("No words returned from Whisper.")

    # ---- BUILD PHRASES OF 4 WORDS (2x2) ----
    phrase = []
    phrase_start = None
    word_counter = 0  # Global counter for rotating colors

    def flush_phrase(phrase_words):
        if not phrase_words:
            return

        # phrase timing (cover full phrase window)
        start_s = phrase_words[0]["start"]
        end_s = phrase_words[-1]["end"]

        # Layout into rows
        top = phrase_words[:2]
        bot = phrase_words[2:4]

        # Compute X positions for each row to be centered
        def row_positions(row_words):
            if not row_words:
                return []
            widths = [approx_text_width_px(PAD_LEFT + w["text"] + PAD_RIGHT) for w in row_words]
            total_w = sum(widths) + GAP_X * (len(row_words) - 1)
            left_x = CENTER_X - total_w // 2

            xs = []
            cursor = left_x
            for w_px in widths:
                # position each tile by its center
                xs.append(cursor + w_px // 2)
                cursor += w_px + GAP_X
            return xs

        top_xs = row_positions(top)
        bot_xs = row_positions(bot)

        # Emit each word as its own tile with its own style (color)
        # Use phrase timing so tiles persist like the screenshot
        # Colors rotate based on global word counter, not position
        nonlocal word_counter
        for idx, w in enumerate(top):
            style_name = STYLE_NAMES[word_counter % len(STYLE_NAMES)]
            ass_lines.append(make_tile_dialogue(start_s, end_s, top_xs[idx], TOP_ROW_Y, w["text"], style_name))
            word_counter += 1

        for idx, w in enumerate(bot):
            style_name = STYLE_NAMES[word_counter % len(STYLE_NAMES)]
            ass_lines.append(make_tile_dialogue(start_s, end_s, bot_xs[idx], BOTTOM_ROW_Y, w["text"], style_name))
            word_counter += 1

    for i, w in enumerate(words):
        if not phrase:
            phrase_start = w["start"]
        phrase.append(w)

        # Flush conditions:
        # - got 4 words
        # - sentence ends
        # - last word
        flush = (
            len(phrase) >= WORDS_PER_PHRASE
            or is_sentence_end(w["text"])
            or i == len(words) - 1
        )

        if flush:
            flush_phrase(phrase)
            phrase = []
            phrase_start = None

    ASS_OUT.write_text("\n".join(ass_lines), encoding="utf-8")
    print(f" Wrote tile captions to: {ASS_OUT}")
    print("    Each word is its own colored box (like your screenshot)")
    print("    2x2 stacked layout")
    print("    Phrase timing (stable, no random missing words)")


if __name__ == "__main__":
    main()
