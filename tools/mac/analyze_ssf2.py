#!/usr/bin/env python3
"""Read-only, streaming resource-size analysis of SSF2 Beta 1.4.0.1 DAT*.ssf files."""
import argparse
import datetime
import re
import struct
import sys
import zlib
from pathlib import Path

CHUNK = 256 * 1024
OUTPUT_CHUNK = 2 * 1024 * 1024
FILE_PATTERN = re.compile(r"DAT([0-9]+)\.ssf", re.I)

def analyze_one(path):
    decoder = zlib.decompressobj()
    total = 0
    prefix = bytearray()
    with path.open("rb") as f:
        while not decoder.eof:
            compressed = f.read(CHUNK)
            if not compressed:
                break
            while compressed:
                decompressed = decoder.decompress(compressed, OUTPUT_CHUNK)
                compressed = decoder.unconsumed_tail
                total += len(decompressed)
                if len(prefix) < 65536:
                    prefix.extend(decompressed[:65536 - len(prefix)])
                if decoder.eof:
                    break
    if not decoder.eof:
        raise ValueError("Incomplete or invalid ZLIB resource")
    extra = decoder.flush()
    total += len(extra)
    if len(prefix) < 65536:
        prefix.extend(extra[:65536 - len(prefix)])
    signature = "unrecognized"
    swf_bytes = None
    if len(prefix) >= 8:
        # AS3 ByteArray defaults to big-endian readInt.
        declared, number_of_ints = struct.unpack_from(">II", prefix)
        start = 8 + number_of_ints * 4
        if number_of_ints < 65536 and start + 3 <= len(prefix) and declared <= total:
            signature = bytes(prefix[start:start + 3]).decode("ascii", "replace")
            if signature in ("FWS", "CWS", "ZWS"):
                swf_bytes = declared
    return (path.stat().st_size, total, swf_bytes, signature)

def fmt(value):
    return f"{value / (1024 * 1024):.2f} MiB"

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data_folder", type=Path, help="Unmodified DAT*.ssf folder")
    parser.add_argument("--output", type=Path, help="Report output")
    args = parser.parse_args()
    folder = args.data_folder.expanduser().resolve()
    if not folder.is_dir():
        parser.error("The selected folder does not exist")
    files = []
    for f in folder.iterdir():
        m = FILE_PATTERN.fullmatch(f.name)
        if m and f.is_file():
            files.append((int(m.group(1)), f))
    files.sort()
    if not files:
        parser.error("No DAT*.ssf files found; choose the data folder")
    records = []
    for i, (num, f) in enumerate(files, 1):
        print(f"[{i}/{len(files)}] {f.name}", flush=True)
        try:
            records.append((num, f.name, *analyze_one(f), ""))
        except Exception as exc:
            records.append((num, f.name, f.stat().st_size, 0, None, "ERROR", str(exc)))
    valid = [v for v in records if not v[-1]]
    missing = [i for i in range(378) if i not in {v[0] for v in records}]
    lines = [
        "SSF2 1.4.0.1 DAT RESOURCE INVENTORY (read-only; no game content)",
        "Generated UTC: " + datetime.datetime.now(datetime.timezone.utc).isoformat(),
        f"DAT files found: {len(records)}; decompressed successfully: {len(valid)}",
        "Absent DAT numbers 0..377: " + (", ".join(map(str, missing)) or "none"),
        "Compressed total: " + fmt(sum(v[2] for v in records)),
        "Decompressed total: " + fmt(sum(v[3] for v in valid)),
        "Note: decompressed resource sizes do not equal RAM consumption.",
        "",
        "LARGEST 30 DECOMPRESSED RESOURCES",
    ]
    for row in sorted(valid, key=lambda row: row[3], reverse=True)[:30]:
        lines.append(f"{row[1]}: {fmt(row[2])} on disk => {fmt(row[3])} expanded; SWF={row[5]}")
    lines.extend(("", "ALL RESOURCES", "filename,compressed_bytes,expanded_bytes,inner_swf_bytes,signature,error"))
    for num, name, compressed, expanded, swfbytes, sig, error in records:
        clean = error.replace(",", ";").replace("\n", " ")
        lines.append(f"{name},{compressed},{expanded},{swfbytes or ''},{sig},{clean}")
    dest = args.output or folder.parent / "SSF2-R36S-resource-report.txt"
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nReport saved: {dest}")
    print("Please upload only the text report, NOT your 900 MB game assets.")
    return 1 if len(valid) != len(records) else 0

if __name__ == "__main__":
    sys.exit(main())
