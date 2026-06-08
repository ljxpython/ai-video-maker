from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "smoke" / "smoke_frame.png"
FONT = Path("/System/Library/Fonts/STHeiti Light.ttc")


def centered_text(draw, text, y, font, fill):
    box = draw.textbbox((0, 0), text, font=font)
    width = box[2] - box[0]
    draw.text(((1920 - width) / 2, y), text, font=font, fill=fill)


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    image = Image.new("RGB", (1920, 1080), (16, 24, 32))
    draw = ImageDraw.Draw(image)

    title_font = ImageFont.truetype(str(FONT), 78)
    subtitle_font = ImageFont.truetype(str(FONT), 44)
    small_font = ImageFont.truetype(str(FONT), 30)

    centered_text(draw, "AI Video Maker", 350, title_font, (255, 255, 255))
    centered_text(draw, "需求对齐 -> 配音字幕 -> 横屏成片", 465, subtitle_font, (255, 209, 102))
    centered_text(draw, "ai-video-maker smoke test", 990, small_font, (128, 143, 160))

    image.save(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    main()
