#!/usr/bin/env python3
"""Extract every terrain chunk's area ID from the game client.

Subzones are defined per terrain chunk: each 533 1/3-yard map tile (ADT) has
16x16 chunks and each chunk header (MCNK) stores one area ID. This reads the
continent tile lists (WDT), then every tile, from local storage, falling back
to Blizzard's CDN for files the client hasn't downloaded. Writes
tools/data/game_areas.json for compare.py and build_borders.py.

Continent WDTs: Eastern Kingdoms and Kalimdor are known. Other continents are
found by scanning for WDT-sized files and matched to a continent ID by tile
overlap with tools/data/subzones.json, or given explicitly with --wdt.

    python extract_game.py
    python extract_game.py --wdt 2991=7198644
"""

import argparse
import json
import struct
import sys
import time
from collections import Counter
from pathlib import Path

from casc import Casc, CascError

ROOT = Path(__file__).resolve().parent
DEFAULT_OUT = ROOT / "data" / "game_areas.json"
DEFAULT_SITE = ROOT / "data" / "subzones.json"
KNOWN_WDTS = {0: 775971, 1: 782779}  # Azeroth (Eastern Kingdoms), Kalimdor
TILE = 1600 / 3
WDT_SIZE_RANGE = (294000, 296000)


def log(*args):
    print(*args, file=sys.stderr, flush=True)


def chunks(data):
    pos = 0
    while pos + 8 <= len(data):
        cid = data[pos:pos + 4][::-1].decode("latin1")
        size = struct.unpack("<I", data[pos + 4:pos + 8])[0]
        yield cid, data[pos + 8:pos + 8 + size]
        pos += 8 + size


def wdt_tiles(data):
    """{(tileX, tileY): rootAdtFdid} from a WDT's MAID chunk."""
    maid = dict(chunks(data)).get("MAID")
    if not maid:
        return {}
    tiles = {}
    for i in range(4096):
        fdid = struct.unpack("<I", maid[i * 32:i * 32 + 4])[0]
        if fdid:
            tiles[(i % 64, i // 64)] = fdid
    return tiles


def adt_areas(data):
    """256 area IDs in row-major chunk order (row = IndexY, col = IndexX)."""
    areas = [0] * 256
    for cid, body in chunks(data):
        if cid == "MCNK":
            index_x, index_y = struct.unpack("<II", body[4:12])
            areas[index_y * 16 + index_x] = struct.unpack("<I", body[0x34:0x38])[0]
    return areas


def find_wdts(storage):
    """fileDataIDs of readable WDTs, found by file size in the encoding table."""
    enc, cs, es = storage._enc, storage._ckey_size, storage._ekey_size
    ckeys = set()
    for page in range(len(storage._page_keys)):
        pos = storage._pages_start + page * storage._page_size
        end = pos + storage._page_size
        while pos + 6 + cs <= end:
            n = enc[pos]
            if n == 0:
                break
            size = int.from_bytes(enc[pos + 1:pos + 6], "big")
            if WDT_SIZE_RANGE[0] <= size <= WDT_SIZE_RANGE[1]:
                ckeys.add(enc[pos + 6:pos + 6 + cs])
            pos += 6 + cs + n * es
    found, encrypted = {}, []
    for fdid in sorted(f for f, ck in storage.by_fdid.items() if ck in ckeys):
        try:
            data = storage.read_fdid(fdid)
        except CascError:
            encrypted.append(fdid)
            continue
        if data[:4] == b"REVM":
            tiles = wdt_tiles(data)
            if tiles:
                found[fdid] = tiles
    return found, encrypted


def site_tiles(site_path):
    """{continentID: set of (tileX, tileY)} covered by the site's subzones."""
    if not site_path.exists():
        return {}
    coverage = {}
    for s in json.loads(site_path.read_text(encoding="utf-8")):
        tiles = coverage.setdefault(int(s["mapId"]), set())
        for ring in s["rings"]:
            for x, y in ring:
                tiles.add((int(32 - y / TILE), int(32 - x / TILE)))
    return coverage


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--wow-dir", default=r"C:\Program Files (x86)\World of Warcraft")
    parser.add_argument("--product", default="wow_classic_beta")
    parser.add_argument("--wdt", action="append", default=[], metavar="CONTINENT=FDID",
                        help="add or override a continent's WDT fileDataID")
    parser.add_argument("--site", type=Path, default=DEFAULT_SITE, help="used only to identify unknown continents")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    started = time.time()
    storage = Casc(args.wow_dir, args.product, log=log)
    log(f"build {storage.version}: {len(storage.by_fdid)} files")

    wdts = dict(KNOWN_WDTS)
    for spec in args.wdt:
        continent, fdid = spec.split("=")
        wdts[int(continent)] = int(fdid)

    log("scanning for continent tile lists...")
    found, encrypted = find_wdts(storage)
    coverage = site_tiles(args.site)
    unmatched = []
    for fdid, tiles in found.items():
        if fdid in wdts.values():
            continue
        # Match to the continent whose site coverage overlaps these tiles most.
        best, best_overlap = None, 0
        for continent, covered in coverage.items():
            if continent in wdts:
                continue
            overlap = len(covered & set(tiles)) / max(1, len(covered))
            if overlap > best_overlap:
                best, best_overlap = continent, overlap
        if best is not None and best_overlap >= 0.8:
            wdts[best] = fdid
            log(f"  WDT {fdid} ({len(tiles)} tiles) -> continent {best} ({best_overlap:.0%} of its site tiles)")
        else:
            unmatched.append((fdid, len(tiles)))
    for fdid, n in unmatched:
        log(f"  WDT {fdid} ({n} tiles) doesn't match a known continent; skipped (use --wdt ID={fdid})")
    if encrypted:
        log(f"  {len(encrypted)} WDT-sized files are encrypted (unreleased content): {encrypted}")

    result = {"build": storage.version, "continents": {}}
    for continent, wdt_fdid in sorted(wdts.items()):
        tiles = found.get(wdt_fdid) or wdt_tiles(storage.read_fdid(wdt_fdid))
        log(f"continent {continent}: WDT {wdt_fdid}, {len(tiles)} tiles")
        out_tiles, skipped = {}, 0
        for n, ((tx, ty), fdid) in enumerate(sorted(tiles.items()), 1):
            try:
                out_tiles[f"{tx}_{ty}"] = adt_areas(storage.read_fdid(fdid))
            except CascError as err:
                skipped += 1
                log(f"  tile {tx}_{ty} (fdid {fdid}): {err}")
            if n % 100 == 0:
                log(f"  {n}/{len(tiles)} tiles  (local {storage.stats['local']}, CDN {storage.stats['cdn']}, "
                    f"cached {storage.stats['cache']})")
        result["continents"][str(continent)] = {"wdt": wdt_fdid, "tiles": out_tiles, "skipped": skipped}
        areas = Counter(a for t in out_tiles.values() for a in t)
        log(f"  done: {len(out_tiles)} tiles, {len(areas)} distinct area IDs, {skipped} skipped")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, separators=(",", ":")), encoding="utf-8")
    log(f"wrote {args.out} in {time.time() - started:.0f}s "
        f"(files: {storage.stats['local']} local, {storage.stats['cdn']} from CDN, {storage.stats['cache']} cached)")


if __name__ == "__main__":
    main()
