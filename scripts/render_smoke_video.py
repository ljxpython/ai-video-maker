import re
from functools import lru_cache
from pathlib import Path

import numpy as np
from moviepy import AudioFileClip, VideoClip
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "output" / "smoke"
AUDIO = OUT_DIR / "demo_narration.mp3"
SRT = OUT_DIR / "demo_narration.srt"
OUTPUT = OUT_DIR / "demo_video.mp4"
FONT = Path("/System/Library/Fonts/STHeiti Light.ttc")

WIDTH = 1920
HEIGHT = 1080
FPS = 24


def parse_time(value):
    hours, minutes, rest = value.split(":")
    seconds, millis = rest.split(",")
    return (
        int(hours) * 3600
        + int(minutes) * 60
        + int(seconds)
        + int(millis) / 1000
    )


def parse_srt(path):
    blocks = re.split(r"\n\s*\n", path.read_text(encoding="utf-8").strip())
    captions = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if len(lines) < 3 or "-->" not in lines[1]:
            continue
        start, end = [part.strip() for part in lines[1].split("-->")]
        captions.append((parse_time(start), parse_time(end), " ".join(lines[2:])))
    return captions


def active_caption(captions, t):
    for start, end, text in captions:
        if start <= t <= end:
            return text
    return ""


def centered_text(draw, text, y, font, fill):
    box = draw.textbbox((0, 0), text, font=font)
    width = box[2] - box[0]
    draw.text(((WIDTH - width) / 2, y), text, font=font, fill=fill)


def wrapped_lines(draw, text, font, max_width):
    if not text:
        return []

    lines = []
    current = ""
    for char in text:
        candidate = current + char
        box = draw.textbbox((0, 0), candidate, font=font)
        if box[2] - box[0] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = char
    if current:
        lines.append(current)
    return lines


@lru_cache(maxsize=32)
def render_frame(caption):
    image = Image.new("RGB", (WIDTH, HEIGHT), (16, 24, 32))
    draw = ImageDraw.Draw(image)

    title_font = ImageFont.truetype(str(FONT), 78)
    subtitle_font = ImageFont.truetype(str(FONT), 44)
    caption_font = ImageFont.truetype(str(FONT), 44)
    small_font = ImageFont.truetype(str(FONT), 30)

    centered_text(draw, "AI Video Maker", 330, title_font, (255, 255, 255))
    centered_text(draw, "需求对齐 -> 配音字幕 -> 横屏成片", 445, subtitle_font, (255, 209, 102))
    centered_text(draw, "ai-video-maker smoke test", 990, small_font, (128, 143, 160))

    lines = wrapped_lines(draw, caption, caption_font, 1500)
    if lines:
        line_height = 64
        block_height = len(lines) * line_height + 32
        top = HEIGHT - 190 - block_height
        left = 220
        right = WIDTH - 220
        bottom = top + block_height
        draw.rounded_rectangle((left, top, right, bottom), radius=18, fill=(0, 0, 0))
        for index, line in enumerate(lines):
            centered_text(draw, line, top + 18 + index * line_height, caption_font, (255, 255, 255))

    return np.asarray(image)


def main():
    captions = parse_srt(SRT)
    audio = AudioFileClip(str(AUDIO))

    def make_frame(t):
        return render_frame(active_caption(captions, t))

    clip = VideoClip(make_frame, duration=audio.duration).with_audio(audio)
    clip.write_videofile(
        str(OUTPUT),
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        bitrate="3500k",
        preset="medium",
    )
    audio.close()
    clip.close()
    print(OUTPUT)


if __name__ == "__main__":
    main()
