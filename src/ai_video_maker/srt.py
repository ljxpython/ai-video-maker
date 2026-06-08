import re
from pathlib import Path


def parse_time(value: str) -> float:
    hours, minutes, rest = value.split(":")
    seconds, millis = rest.split(",")
    return (
        int(hours) * 3600
        + int(minutes) * 60
        + int(seconds)
        + int(millis) / 1000
    )


def parse_srt(path: Path) -> list[tuple[float, float, str]]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []

    blocks = re.split(r"\n\s*\n", text)
    captions = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if len(lines) < 3 or "-->" not in lines[1]:
            continue
        start, end = [part.strip() for part in lines[1].split("-->")]
        captions.append((parse_time(start), parse_time(end), " ".join(lines[2:])))
    return captions


def active_caption(captions: list[tuple[float, float, str]], t: float) -> str:
    for start, end, text in captions:
        if start <= t <= end:
            return text
    return ""
