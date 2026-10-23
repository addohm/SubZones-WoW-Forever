#!/usr/bin/env python3
"""Package the addon into release/SUBZONES-<version>.zip for CurseForge / Wago.

    python tools/package.py

The zip holds a top-level SUBZONES/ folder with the TOC, the files it loads and the
files it points to (the icon), plus the repo's LICENSE (GPLv3). The version comes from the TOC's ## Version line.
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


def toc_assets(text):
    """Files named by ## IconTexture, which the client looks up without an extension."""
    names = []
    for path in re.findall(r"^## IconTexture:\s*(\S+)", text, re.MULTILINE):
        stem = path.replace("\\", "/").rsplit("/", 1)[-1]
        names += [p.name for p in ADDON.glob(stem + ".*")]
    if not names:
        sys.exit("## IconTexture points to no file in SUBZONES/")
    return names


def main():
    text = TOC.read_text(encoding="utf-8")
    out = RELEASE / f"SUBZONES-{toc_version(text)}.zip"
    RELEASE.mkdir(exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name in [TOC.name] + toc_files(text) + toc_assets(text):
            z.write(ADDON / name, f"SUBZONES/{name}")
        # GPLv3 requires the license text to travel with every copy.
        z.write(ROOT / "LICENSE", "SUBZONES/LICENSE")
    print(f"wrote {out.relative_to(ROOT)} ({out.stat().st_size // 1024} KB)", file=sys.stderr)


if __name__ == "__main__":
    main()
