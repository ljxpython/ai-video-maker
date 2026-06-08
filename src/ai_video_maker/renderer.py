from functools import lru_cache
from pathlib import Path

import numpy as np
from moviepy import AudioFileClip, VideoClip
from PIL import Image, ImageDraw, ImageFont

from .srt import active_caption, parse_srt


WIDTH = 1920
HEIGHT = 1080
DEFAULT_FONT = Path("/System/Library/Fonts/STHeiti Light.ttc")


def centered_text(draw: ImageDraw.ImageDraw, text: str, y: int, font: ImageFont.FreeTypeFont, fill: tuple[int, int, int]) -> None:
    box = draw.textbbox((0, 0), text, font=font)
    width = box[2] - box[0]
    draw.text(((WIDTH - width) / 2, y), text, font=font, fill=fill)


def wrapped_lines(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
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


def render_video(
    *,
    audio_path: Path,
    subtitles_path: Path,
    output_path: Path,
    title: str,
    subtitle: str,
    footer: str,
    fps: int = 24,
    bitrate: str = "3500k",
) -> Path:
    captions = parse_srt(subtitles_path)
    audio = AudioFileClip(str(audio_path))

    @lru_cache(maxsize=64)
    def render_frame(caption: str) -> np.ndarray:
        image = Image.new("RGB", (WIDTH, HEIGHT), (16, 24, 32))
        draw = ImageDraw.Draw(image)

        title_font = ImageFont.truetype(str(DEFAULT_FONT), 78)
        subtitle_font = ImageFont.truetype(str(DEFAULT_FONT), 44)
        caption_font = ImageFont.truetype(str(DEFAULT_FONT), 44)
        small_font = ImageFont.truetype(str(DEFAULT_FONT), 30)

        centered_text(draw, title, 330, title_font, (255, 255, 255))
        centered_text(draw, subtitle, 445, subtitle_font, (255, 209, 102))
        centered_text(draw, footer, 990, small_font, (128, 143, 160))

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

    def make_frame(t: float) -> np.ndarray:
        return render_frame(active_caption(captions, t))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    clip = VideoClip(make_frame, duration=audio.duration).with_audio(audio)
    clip.write_videofile(
        str(output_path),
        fps=fps,
        codec="libx264",
        audio_codec="aac",
        bitrate=bitrate,
        preset="medium",
    )
    audio.close()
    clip.close()
    return output_path
