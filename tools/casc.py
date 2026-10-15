"""Read-only access to WoW game files: local CASC storage with Blizzard CDN fallback.

Files are looked up by fileDataID or by path. Anything not stored locally (the
client streams many files on demand) is fetched from Blizzard's CDN using the
install's own CDN config and cached archive indices, then kept in tools/cache.

    storage = Casc(r"C:/Program Files (x86)/World of Warcraft", "wow_classic_beta")
    data = storage.read_path("World/Maps/Kalimdor/Kalimdor.wdt")
    data = storage.read_fdid(782779)

Only the standard library is used. Encrypted BLTE chunks raise CascError.
"""

import bisect
import struct
import sys
import urllib.request
import zlib
from pathlib import Path

CACHE_DIR = Path(__file__).resolve().parent / "cache" / "cdn"
USER_AGENT = "SubzoneOverlay-datagen"


class CascError(Exception):
    pass


# --- BLTE ---------------------------------------------------------------------

def blte_decode(data):
    if data[:4] != b"BLTE":
        raise CascError("not a BLTE stream")
    header_size = struct.unpack(">I", data[4:8])[0]
    if header_size == 0:
        chunks = [data[8:]]
    else:
        count = struct.unpack(">I", b"\0" + data[9:12])[0]
        pos, offset, chunks = 12, header_size, []
        for _ in range(count):
            comp_size = struct.unpack(">I", data[pos:pos + 4])[0]
            chunks.append(data[offset:offset + comp_size])
            offset += comp_size
            pos += 24
    out = bytearray()
    for chunk in chunks:
        mode, body = chunk[:1], chunk[1:]
        if mode == b"N":
            out += body
        elif mode == b"Z":
            out += zlib.decompress(body)
        elif mode == b"F":
            out += blte_decode(body)
        elif mode == b"E":
            raise CascError("encrypted chunk")
        else:
            raise CascError(f"unsupported BLTE mode {mode!r}")
    return bytes(out)


# --- Jenkins lookup3 hashlittle2, used for root name hashes -------------------

def _rot(x, k):
    return ((x << k) | (x >> (32 - k))) & 0xFFFFFFFF


def hashlittle2(data, pc=0, pb=0):
    length = len(data)
    a = b = c = (0xDEADBEEF + length + pc) & 0xFFFFFFFF
    c = (c + pb) & 0xFFFFFFFF
    pos = 0
    while length > 12:
        a = (a + int.from_bytes(data[pos:pos + 4], "little")) & 0xFFFFFFFF
        b = (b + int.from_bytes(data[pos + 4:pos + 8], "little")) & 0xFFFFFFFF
        c = (c + int.from_bytes(data[pos + 8:pos + 12], "little")) & 0xFFFFFFFF
        a = (a - c) & 0xFFFFFFFF; a ^= _rot(c, 4); c = (c + b) & 0xFFFFFFFF
        b = (b - a) & 0xFFFFFFFF; b ^= _rot(a, 6); a = (a + c) & 0xFFFFFFFF
        c = (c - b) & 0xFFFFFFFF; c ^= _rot(b, 8); b = (b + a) & 0xFFFFFFFF
        a = (a - c) & 0xFFFFFFFF; a ^= _rot(c, 16); c = (c + b) & 0xFFFFFFFF
        b = (b - a) & 0xFFFFFFFF; b ^= _rot(a, 19); a = (a + c) & 0xFFFFFFFF
        c = (c - b) & 0xFFFFFFFF; c ^= _rot(b, 4); b = (b + a) & 0xFFFFFFFF
        length -= 12
        pos += 12
    if length == 0:
        return c, b
    tail = data[pos:] + b"\0" * (12 - length)
    a = (a + int.from_bytes(tail[0:4], "little")) & 0xFFFFFFFF
    b = (b + int.from_bytes(tail[4:8], "little")) & 0xFFFFFFFF
    c = (c + int.from_bytes(tail[8:12], "little")) & 0xFFFFFFFF
    c ^= b; c = (c - _rot(b, 14)) & 0xFFFFFFFF
    a ^= c; a = (a - _rot(c, 11)) & 0xFFFFFFFF
    b ^= a; b = (b - _rot(a, 25)) & 0xFFFFFFFF
    c ^= b; c = (c - _rot(b, 16)) & 0xFFFFFFFF
    a ^= c; a = (a - _rot(c, 4)) & 0xFFFFFFFF
    b ^= a; b = (b - _rot(a, 14)) & 0xFFFFFFFF
    c ^= b; c = (c - _rot(b, 24)) & 0xFFFFFFFF
    return c, b


def name_hash(path):
    pc, pb = hashlittle2(path.replace("/", "\\").upper().encode("ascii"))
    return (pc << 32) | pb


# --- Storage ------------------------------------------------------------------

def _read_config(path):
    config = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if " = " in line:
            k, v = line.split(" = ", 1)
            config[k.strip()] = v.split()
    return config


class Casc:
    def __init__(self, wow_dir, product, log=print):
        self.root_dir = Path(wow_dir)
        self.data_dir = self.root_dir / "Data"
        self.log = log
        self.stats = {"local": 0, "cdn": 0, "cache": 0}
        self._read_build_info(product)
        self.build_config = _read_config(self._config_path(self.build_key))
        self.cdn_config = _read_config(self._config_path(self.cdn_key))
        self.local_index = self._load_local_indices(product)
        self.cdn_index = None  # loaded on first CDN miss
        self._load_encoding()
        self._load_root()

    def _config_path(self, key):
        return self.data_dir / "config" / key[:2] / key[2:4] / key

    def _read_build_info(self, product):
        lines = (self.root_dir / ".build.info").read_text(encoding="utf-8").splitlines()
        header = [h.split("!")[0] for h in lines[0].split("|")]
        for line in lines[1:]:
            row = dict(zip(header, line.split("|")))
            if row.get("Product") == product and row.get("Active") == "1":
                self.build_key, self.cdn_key = row["Build Key"], row["CDN Key"]
                self.version = row.get("Version", "")
                self.cdn_path = row["CDN Path"]
                self.cdn_hosts = row["CDN Hosts"].split()
                return
        raise CascError(f"product {product} not in .build.info")

    # local storage

    def _load_local_indices(self, product):
        index = {}
        for folder in (self.data_dir / product, self.data_dir / "data"):
            latest = {}
            for path in folder.glob("*.idx"):
                bucket, version = path.stem[:2], int(path.stem[2:], 16)
                if bucket not in latest or version > latest[bucket][0]:
                    latest[bucket] = (version, path)
            for _, path in latest.values():
                raw = path.read_bytes()
                header_size = struct.unpack("<I", raw[0:4])[0]
                _, _, _, size_len, offset_len, key_len, offset_bits, _ = struct.unpack(
                    "<HBBBBBBQ", raw[8:8 + header_size])
                pos = (8 + header_size + 15) & ~15
                end = pos + 8 + struct.unpack("<I", raw[pos:pos + 4])[0]
                pos += 8
                entry_len = key_len + offset_len + size_len
                mask = (1 << offset_bits) - 1
                while pos + entry_len <= end:
                    key = raw[pos:pos + key_len]
                    if key not in index:
                        packed = int.from_bytes(raw[pos + key_len:pos + key_len + offset_len], "big")
                        size = int.from_bytes(raw[pos + key_len + offset_len:pos + entry_len], "little")
                        index[key] = (packed >> offset_bits, packed & mask, size)
                    pos += entry_len
        return index

    def _read_local(self, ekey):
        entry = self.local_index.get(ekey[:9])
        if entry is None:
            return None
        archive, offset, size = entry
        path = self.data_dir / "data" / f"data.{archive:03d}"
        if not path.exists():
            return None
        with open(path, "rb") as fh:
            fh.seek(offset)
            header = fh.read(30)
            # The entry header stores the full ekey byte-reversed; a mismatch
            # means the slot was reused and the file is no longer resident.
            if header[:16][::-1][:9] != ekey[:9]:
                return None
            return fh.read(size - 30)

    # Blizzard CDN

    def _cdn_get(self, url_path, byte_range=None):
        last = None
        for host in self.cdn_hosts:
            url = f"http://{host}/{self.cdn_path}/{url_path}"
            headers = {"User-Agent": USER_AGENT}
            if byte_range:
                headers["Range"] = f"bytes={byte_range[0]}-{byte_range[0] + byte_range[1] - 1}"
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as resp:
                    return resp.read()
            except OSError as err:
                last = err
        raise CascError(f"CDN fetch failed for {url_path}: {last}")

    def _load_cdn_index(self):
        self.cdn_index = {}
        archives = self.cdn_config.get("archives", [])
        missing = 0
        for archive in archives:
            path = self.data_dir / "indices" / f"{archive}.index"
            if not path.exists():
                path = CACHE_DIR / f"{archive}.index"
                if not path.exists():
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(self._cdn_get(f"data/{archive[:2]}/{archive[2:4]}/{archive}.index"))
                    missing += 1
            raw = path.read_bytes()
            block_kb, offset_bytes, size_bytes, key_bytes, check_bytes = raw[-17], raw[-16], raw[-15], raw[-14], raw[-13]
            block = block_kb * 1024
            blocks = (len(raw) - 28) // (block + key_bytes + check_bytes)
            entry = key_bytes + size_bytes + offset_bytes
            for b in range(blocks):
                pos, end = b * block, b * block + block
                while pos + entry <= end:
                    key = raw[pos:pos + key_bytes]
                    if not any(key):
                        break
                    size = int.from_bytes(raw[pos + key_bytes:pos + key_bytes + size_bytes], "big")
                    offset = int.from_bytes(raw[pos + key_bytes + size_bytes:pos + entry], "big")
                    self.cdn_index.setdefault(key[:9], (archive, offset, size))
                    pos += entry
        if missing:
            self.log(f"  downloaded {missing} archive indices from the CDN")

    def _read_cdn(self, ekey):
        cached = CACHE_DIR / "files" / ekey.hex()
        if cached.exists():
            self.stats["cache"] += 1
            return cached.read_bytes()
        if self.cdn_index is None:
            self._load_cdn_index()
        entry = self.cdn_index.get(ekey[:9])
        if entry:
            archive, offset, size = entry
            data = self._cdn_get(f"data/{archive[:2]}/{archive[2:4]}/{archive}", (offset, size))
        else:  # unarchived ("loose") file
            key = ekey.hex()
            data = self._cdn_get(f"data/{key[:2]}/{key[2:4]}/{key}")
        cached.parent.mkdir(parents=True, exist_ok=True)
        cached.write_bytes(data)
        self.stats["cdn"] += 1
        return data

    def read_ekey(self, ekey):
        data = self._read_local(ekey)
        if data is not None:
            self.stats["local"] += 1
            return blte_decode(data)
        return blte_decode(self._read_cdn(ekey))

    # encoding: ckey -> ekey

    def _load_encoding(self):
        enc = self.read_ekey(bytes.fromhex(self.build_config["encoding"][1]))
        if enc[:2] != b"EN":
            raise CascError("bad encoding file")
        _, ckey_size, ekey_size, page_kb, _, page_count, _, _, espec_size = struct.unpack(">BBBHHIIBI", enc[2:22])
        pos = 22 + espec_size
        self._enc, self._ckey_size, self._ekey_size = enc, ckey_size, ekey_size
        self._page_size = page_kb * 1024
        self._page_keys = []
        for _ in range(page_count):
            self._page_keys.append(enc[pos:pos + ckey_size])
            pos += ckey_size + 16
        self._pages_start = pos

    def ckey_to_ekey(self, ckey):
        page = bisect.bisect_right(self._page_keys, ckey) - 1
        if page < 0:
            return None
        pos = self._pages_start + page * self._page_size
        end = pos + self._page_size
        enc, cs, es = self._enc, self._ckey_size, self._ekey_size
        while pos + 6 + cs <= end:
            count = enc[pos]
            if count == 0:
                break
            if enc[pos + 6:pos + 6 + cs] == ckey:
                return enc[pos + 6 + cs:pos + 6 + cs + es]
            pos += 6 + cs + count * es
        return None

    # root: fileDataID / name hash -> ckey

    def _load_root(self):
        ekey = self.ckey_to_ekey(bytes.fromhex(self.build_config["root"][0]))
        if ekey is None:
            raise CascError("root not in encoding")
        data = self.read_ekey(ekey)
        if data[:4] != b"TSFM":
            raise CascError("unsupported (pre-8.2) root format")
        a, b = struct.unpack("<II", data[4:12])
        version, pos = (b, a) if a in (0x14, 0x18) and b in (1, 2) else (1, 12)
        self.by_fdid, self.by_name = {}, {}
        preferred = set()
        while pos < len(data):
            if version >= 2:
                count, locale, f1, f2, f3 = struct.unpack("<IIIIB", data[pos:pos + 17])
                content_flags = f1 | f2 | (f3 << 17)
                pos += 17
            else:
                count, content_flags, locale = struct.unpack("<III", data[pos:pos + 12])
                pos += 12
            wanted_locale = locale & 0x2 or locale == 0xFFFFFFFF  # enUS or all
            deltas = struct.unpack(f"<{count}i", data[pos:pos + 4 * count])
            pos += 4 * count
            ckeys = pos
            pos += 16 * count
            hashes = None
            if not content_flags & 0x10000000:
                hashes = pos
                pos += 8 * count
            fdid = -1
            for i, delta in enumerate(deltas):
                fdid += 1 + delta
                # First enUS/all-locale entry wins; other locales only fill gaps.
                if wanted_locale and fdid not in preferred:
                    preferred.add(fdid)
                    self.by_fdid[fdid] = data[ckeys + 16 * i:ckeys + 16 * i + 16]
                elif fdid not in self.by_fdid:
                    self.by_fdid[fdid] = data[ckeys + 16 * i:ckeys + 16 * i + 16]
                if hashes is not None:
                    h = struct.unpack("<Q", data[hashes + 8 * i:hashes + 8 * i + 8])[0]
                    self.by_name.setdefault(h, fdid)

    def fdid_for_path(self, path):
        return self.by_name.get(name_hash(path))

    def read_fdid(self, fdid):
        ckey = self.by_fdid.get(fdid)
        if ckey is None:
            raise CascError(f"fileDataID {fdid} not in root")
        ekey = self.ckey_to_ekey(ckey)
        if ekey is None:
            raise CascError(f"fileDataID {fdid} not in encoding")
        return self.read_ekey(ekey)

    def read_path(self, path):
        fdid = self.fdid_for_path(path)
        if fdid is None:
            raise CascError(f"{path} not in root (no name hash)")
        return self.read_fdid(fdid)


if __name__ == "__main__":
    storage = Casc(sys.argv[1], sys.argv[2])
    print(f"{storage.version}: {len(storage.by_fdid)} files, {len(storage.by_name)} named")
