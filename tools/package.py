#!/usr/bin/env python3
"""Package the addon into release/SUBZONES-<version>.zip for CurseForge / Wago.

    python tools/package.py

The zip holds a top-level SUBZONES/ folder with only the files the TOC loads,
plus the TOC itself. The version comes from the TOC's ## Version line.
"""
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ADDON = ROOT / "SUBZONES"
TOC = ADDON / "SUBZONES.toc"
RELEASE = ROOT / "release"


def toc_version(text):
    match = re.search(r"^## Version:\s*(\S+)", text, re.MULTILINE)
    if not match:
        sys.exit("no ## Version in SUBZONES.toc")
    return match.group(1)


def toc_files(text):
    return [line.strip() for line in text.splitlines() if line.strip() and not line.startswith("#")]


def main():
    text = TOC.read_text(encoding="utf-8")
    out = RELEASE / f"SUBZONES-{toc_version(text)}.zip"
    RELEASE.mkdir(exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name in [TOC.name] + toc_files(text):
            z.write(ADDON / name, f"SUBZONES/{name}")
    print(f"wrote {out.relative_to(ROOT)} ({out.stat().st_size // 1024} KB)", file=sys.stderr)


if __name__ == "__main__":
    main()
