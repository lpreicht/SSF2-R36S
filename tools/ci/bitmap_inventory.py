#!/usr/bin/env python3
"""Analyze duplicated SWF bitmap assets from official SSF2 ZIP; outputs sizes/hashes only."""
from pathlib import Path
import argparse
import collections
import hashlib
import io
import json
import re
import struct
import zipfile
import zlib

from PIL import Image

BITMAP_TAGS = {6, 20, 21, 35, 36, 90}
DATA_PATTERN = re.compile(r"(?:^|/)data/DAT\d+\.ssf$", re.I)

def tags(binary, begin, end, depth=0):
    if depth > 6 or begin < 0 or begin >= end:
        return
    cursor = begin
    while cursor + 2 <= end:
        info, = struct.unpack_from("<H", binary, cursor)
        cursor += 2
        code = info >> 6
        length = info & 0x3f
        if length == 63:
            if cursor + 4 > end:
                return
            length, = struct.unpack_from("<I", binary, cursor)
            cursor += 4
        after = cursor + length
        if after > end or after < cursor:
            return
        if code == 0:
            return
        if code in BITMAP_TAGS:
            yield code, binary[cursor:after]
        elif code == 39 and length >= 4:  # DefineSprite; SpriteId and FrameCount
            yield from tags(binary, cursor + 4, after, depth + 1)
        cursor = after

def bitmap_dimensions(code, payload):
    if len(payload) < 2:
        return None
    if code in (20, 36) and len(payload) >= 7:
        w, h = struct.unpack_from("<HH", payload, 3)
        return (w, h)
    # SWF JPEG2: 2 ID bytes followed by JPEG; JPEG3 adds u32 alpha offset;
    # JPEG4 adds u32 alpha offset and u16 deblocking fixed-point value.
    if code in (6, 21):
        jpeg = payload[2:]
    elif code in (35, 90) and len(payload) >= 6:
        length, = struct.unpack_from("<I", payload, 2)
        start = 6 if code == 35 else 8
        jpeg = payload[start:start+length]
    else:
        return None
    try:
        with Image.open(io.BytesIO(jpeg)) as image:
            return image.size
    except Exception:
        return None

def find_swf(data):
    # The DAT wrapper has already been unpacked with outer ZLIB.
    # The embedded SWF begins after a small per-file metadata prefix.
    pos = data.find(b"FWS", 0, min(len(data), 65536))
    if pos == -1 or pos+9 >= len(data):
        return None
    version = data[pos+3]
    declared = int.from_bytes(data[pos+4:pos+8], "little")
    if not (8 <= version <= 50 and 8 <= declared <= len(data)-pos+8):
        return None
    raw = memoryview(data)[pos:]
    rect_bits = raw[8] >> 3
    rect_len = (5 + 4*rect_bits + 7) // 8
    first_tag = 8 + rect_len + 4  # RECT + frame rate + frame count
    return raw, first_tag

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("zipfile")
    parser.add_argument("output")
    args = parser.parse_args()
    counts = collections.Counter()
    records = collections.Counter()
    examples = {}
    filecount = 0
    rejected = []
    for_name = {}
    sizes = []
    with zipfile.ZipFile(args.zipfile) as archive:
        for entry in archive.infolist():
            if not DATA_PATTERN.search(entry.filename):
                continue
            filecount += 1
            if filecount % 40 == 0:
                print(f"SWF bitmap scan: {filecount} DAT archives", flush=True)
            try:
                raw = zlib.decompress(archive.read(entry))
                located = find_swf(raw)
                if located is None:
                    rejected.append(entry.filename + " (no FWS)")
                    continue
                swf, offset = located
                for code, payload in tags(swf, offset, len(swf)):
                    if len(payload) < 2:
                        continue
                    dimensions = bitmap_dimensions(code, payload)
                    hashvalue = hashlib.sha256(bytes([code]) + bytes(payload[2:])).hexdigest()
                    key = f"{code}:{hashvalue}"
                    counts[key] += 1
                    records[key] = (len(payload), dimensions)
                    examples.setdefault(key, entry.filename.split("/")[-1])
                    if dimensions and 0 < dimensions[0] <= 8192 and 0 < dimensions[1] <= 8192:
                        sizes.append(dimensions[0]*dimensions[1]*4)
            except Exception as error:
                rejected.append(f"{entry.filename} ({type(error).__name__}: {error})")
    unique_size = sum(records[k][0] for k in counts)
    total_size = sum(records[k][0] * count for k, count in counts.items())
    duplicate_size = total_size - unique_size
    theoretical_ram = sum(sizes)
    theoretical_unique = sum(
        dims[0]*dims[1]*4 for (length, dims) in records.values()
        if dims and 0 < dims[0] <= 8192 and 0 < dims[1] <= 8192
    )
    theoretical_duplicates = theoretical_ram - theoretical_unique
    report = [
        "SSF2 1.4.0.1 — bitmap tag inventory (official game assets; no game data)",
        "All values are theoretical resource sizes, not measured game RAM.",
        f"DAT files scanned: {filecount}",
        f"Unreadable/invalid embedded SWFs: {len(rejected)}",
        f"Bitmap tags total: {sum(counts.values())}",
        f"Unique bitmap tags by SHA256: {len(counts)}",
        f"Repeated tag instances: {sum(n-1 for n in counts.values())}",
        f"Total compressed bitmap tag bytes: {total_size:,}",
        f"Unique compressed bitmap tag bytes: {unique_size:,}",
        f"Repeated compressed tag bytes: {duplicate_size:,} ({duplicate_size / max(total_size,1)*100:.1f}%)",
        f"Known-dimension bitmap tags: {len(sizes)}",
        f"Theoretical 4-byte/pixel sum (not live allocation): {theoretical_ram/1048576:.2f} MiB",
        f"Theoretical unique-content RGBA sum: {theoretical_unique/1048576:.2f} MiB",
        f"Theoretical duplicate RGBA reduction: {theoretical_duplicates/1048576:.2f} MiB ({theoretical_duplicates/max(theoretical_ram,1)*100:.1f}%)",
        "",
        "Top 30 repeated bitmap tags (hash prefixes only; no game data):",
    ]
    for key,count in sorted(counts.items(),key=lambda z:(z[1]-1)*records[z[0]][0],reverse=True)[:30]:
        length, dimensions = records[key]
        report.append(f"occurrences={count} tag={key.split(':')[0]} bytes_each={length} size={dimensions} original_file={examples[key]} sha256={key.split(':')[1][:12]}")
    report.extend(["", "Invalid entries:"] + rejected[:100])
    Path(args.output).write_text("\n".join(report)+"\n",encoding="utf-8")
    print("\n".join(report[:13]), flush=True)

if __name__ == "__main__":
    main()
