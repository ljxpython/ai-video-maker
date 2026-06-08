from functools import lru_cache
from pathlib import Path

import numpy as np
from moviepy import AudioFileClip, ColorClip, CompositeVideoClip, ImageClip, TextClip, VideoClip, VideoFileClip, concatenate_videoclips
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


def render_mixed_video(
    *,
    audio_path: Path,
    subtitles_path: Path,
    storyboard: dict,
    output_path: Path,
    browser_recording_path: Path | None = None,
    terminal_card_paths: list[Path] | None = None,
    width: int = WIDTH,
    height: int = HEIGHT,
    fps: int = 24,
    bitrate: str = "3500k",
) -> Path:
    audio = AudioFileClip(str(audio_path))
    captions = parse_srt(subtitles_path)
    sections = [section for section in storyboard.get("sections", []) if isinstance(section, dict)]
    if not sections:
        sections = [{"id": "summary", "duration": max(1, round(audio.duration)), "visual": storyboard.get("title", ""), "narration": ""}]

    clips = []
    recording_used = False
    terminal_cards = [path for path in (terminal_card_paths or []) if path.exists()]
    terminal_card_used = False
    for section in sections:
        duration = max(1, int(section.get("duration", 1)))
        if browser_recording_path and browser_recording_path.exists() and not recording_used and str(section.get("id", "")) in {"steps", "demo", "capture"}:
            clip = _browser_clip(browser_recording_path, duration, width, height)
            recording_used = True
        elif terminal_cards and not terminal_card_used and str(section.get("id", "")) in {"steps", "demo", "capture"}:
            clip = _image_clip(terminal_cards[0], duration, width, height)
            terminal_card_used = True
        else:
            clip = _card_clip_sized(storyboard, section, duration, fps, width, height)
        clips.append(clip)

    video = concatenate_videoclips(clips, method="compose")
    if video.duration < audio.duration:
        video = concatenate_videoclips([video, _card_clip_sized(storyboard, sections[-1], audio.duration - video.duration, fps, width, height)], method="compose")
    if video.duration > audio.duration:
        video = video.subclipped(0, audio.duration)

    caption_layer = VideoClip(lambda t: _caption_frame_sized(active_caption(captions, t), width, height), duration=audio.duration)
    caption_layer = caption_layer.with_position(("center", "bottom"))
    composed = CompositeVideoClip([video, caption_layer], size=(width, height)).with_audio(audio)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    composed.write_videofile(
        str(output_path),
        fps=fps,
        codec="libx264",
        audio_codec="aac",
        bitrate=bitrate,
        preset="medium",
    )
    for clip in clips:
        clip.close()
    video.close()
    caption_layer.close()
    audio.close()
    composed.close()
    return output_path


def _card_clip(storyboard: dict, section: dict, duration: float, fps: int) -> VideoClip:
    return _card_clip_sized(storyboard, section, duration, fps, WIDTH, HEIGHT)


def _card_clip_sized(storyboard: dict, section: dict, duration: float, fps: int, width: int, height: int) -> VideoClip:
    title = str(storyboard.get("title", "AI Video Maker"))
    visual = str(section.get("visual", section.get("purpose", "")))
    narration = str(section.get("narration", ""))

    @lru_cache(maxsize=1)
    def frame() -> np.ndarray:
        image = Image.new("RGB", (width, height), (18, 26, 36))
        draw = ImageDraw.Draw(image)
        scale = min(width / WIDTH, height / HEIGHT)
        title_font = ImageFont.truetype(str(DEFAULT_FONT), max(34, round(64 * scale)))
        body_font = ImageFont.truetype(str(DEFAULT_FONT), max(28, round(42 * scale)))
        small_font = ImageFont.truetype(str(DEFAULT_FONT), max(22, round(30 * scale)))

        _centered_text(draw, title, round(height * 0.13), title_font, (255, 255, 255), width)
        y = round(height * 0.30)
        max_width = round(width * 0.78)
        for line in wrapped_lines(draw, visual, body_font, max_width)[:5]:
            _centered_text(draw, line, y, body_font, (255, 209, 102), width)
            y += round(58 * scale)
        y += 32
        for line in wrapped_lines(draw, narration, small_font, max_width)[:4]:
            _centered_text(draw, line, y, small_font, (198, 211, 225), width)
            y += round(42 * scale)
        _centered_text(draw, f"section: {section.get('id', '')}", height - round(80 * scale), small_font, (128, 143, 160), width)
        return np.asarray(image)

    return VideoClip(lambda _t: frame(), duration=duration).with_fps(fps)


def _browser_clip(path: Path, duration: float, width: int = WIDTH, height: int = HEIGHT) -> VideoClip:
    clip = VideoFileClip(str(path))
    if clip.duration > duration:
        clip = clip.subclipped(0, duration)
    elif clip.duration < duration:
        padding = ColorClip(size=(width, height), color=(18, 26, 36), duration=duration - clip.duration)
        clip = concatenate_videoclips([clip, padding], method="compose")
    resized = clip.resized(height=height)
    if resized.w < width:
        resized = clip.resized(width=width)
    return resized.cropped(x_center=resized.w / 2, y_center=resized.h / 2, width=width, height=height).with_position(("center", "center"))


def _image_clip(path: Path, duration: float, width: int, height: int) -> VideoClip:
    clip = ImageClip(str(path)).with_duration(duration)
    resized = clip.resized(width=round(width * 0.9))
    if resized.h > height * 0.72:
        resized = clip.resized(height=round(height * 0.72))
    background = ColorClip(size=(width, height), color=(18, 26, 36), duration=duration)
    return CompositeVideoClip([background, resized.with_position(("center", "center"))], size=(width, height))


def _caption_frame(caption: str) -> np.ndarray:
    return _caption_frame_sized(caption, WIDTH, HEIGHT)


def _caption_frame_sized(caption: str, width: int, height: int) -> np.ndarray:
    layer_height = max(180, round(height * 0.22))
    image = Image.new("RGBA", (width, layer_height), (0, 0, 0, 0))
    if not caption:
        return np.asarray(image)
    draw = ImageDraw.Draw(image)
    scale = min(width / WIDTH, height / HEIGHT)
    font = ImageFont.truetype(str(DEFAULT_FONT), max(28, round(42 * scale)))
    max_width = round(width * 0.78)
    lines = wrapped_lines(draw, caption, font, max_width)
    line_height = max(38, round(56 * scale))
    block_height = len(lines) * line_height + 30
    top = layer_height - block_height - max(18, round(24 * scale))
    left = round(width * 0.11)
    draw.rounded_rectangle((left, top, width - left, top + block_height), radius=18, fill=(0, 0, 0, 210))
    for index, line in enumerate(lines):
        _centered_text(draw, line, top + 16 + index * line_height, font, (255, 255, 255), width)
    return np.asarray(image)


def _centered_text(draw: ImageDraw.ImageDraw, text: str, y: int, font: ImageFont.FreeTypeFont, fill: tuple[int, int, int], width: int) -> None:
    box = draw.textbbox((0, 0), text, font=font)
    text_width = box[2] - box[0]
    draw.text(((width - text_width) / 2, y), text, font=font, fill=fill)
