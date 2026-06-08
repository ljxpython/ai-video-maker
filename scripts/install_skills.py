#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import yaml


def main() -> None:
    parser = argparse.ArgumentParser(description="Install ai-video-maker skills")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--copy", action="store_true")
    mode.add_argument("--link", action="store_true")
    mode.add_argument("--dry-run", action="store_true")
    parser.add_argument("--target", required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    manifest = yaml.safe_load((project_root / "skills" / "manifest.yml").read_text(encoding="utf-8"))
    target = Path(args.target).expanduser()
    dry_run = args.dry_run or not args.copy and not args.link
    action = "dry-run" if dry_run else "link" if args.link else "copy"
    results = []
    if not dry_run:
        target.mkdir(parents=True, exist_ok=True)

    for skill in manifest.get("skills", []):
        source = project_root / skill["path"]
        destination = target / skill["name"]
        if destination.exists() and not args.force:
            results.append((skill["name"], "skipped", "already exists"))
            continue
        if dry_run:
            results.append((skill["name"], "planned", action))
            continue
        if destination.exists() and args.force:
            if destination.is_symlink() or destination.is_file():
                destination.unlink()
            else:
                shutil.rmtree(destination)
        if args.link:
            destination.symlink_to(source, target_is_directory=True)
        else:
            shutil.copytree(source, destination)
        results.append((skill["name"], "installed", action))

    for name, status, detail in results:
        print(f"{status}: {name} ({detail})")

if __name__ == "__main__":
    main()
