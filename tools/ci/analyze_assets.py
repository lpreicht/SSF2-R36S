#!/usr/bin/env python3
"""Size-only analysis of official SSF2 data files. Never saves game resources."""
import sys
import zipfile
import zlib
import re
import time
from pathlib import Path

zip_path = Path(sys.argv[1])
out = Path(sys.argv[2])
pattern = re.compile(r'(?:^|/)data/(DAT(\\d+)\\.ssf)$', re.I)
print(f'Examining {zip_path.name}: {zip_path.stat().st_size/1048576:.1f} MiB', flush=True)
with zipfile.ZipFile(zip_path) as z:
    infos = []
    for info in z.infolist():
        match = pattern.search(info.filename)
        if match and not info.is_dir():
            infos.append((int(match.group(2)), info))
    infos.sort(key=lambda item: item[0])
    print(f'DAT archives found: {len(infos)}', flush=True)
    if len(infos) < 100:
        raise RuntimeError('Too few DAT files in downloaded official archive')
    rows = []
    start = time.monotonic()
    for n, (index, info) in enumerate(infos, 1):
        expanded = 0
        error = ''
        dec = zlib.decompressobj()
        try:
            with z.open(info) as source:
                while not dec.eof:
                    block = source.read(128 * 1024)
                    if not block:
                        break
                    while block:
                        chunk = dec.decompress(block, 1024 * 1024)
                        block = dec.unconsumed_tail
                        expanded += len(chunk)
                        if dec.eof:
                            break
            if not dec.eof:
                error = 'zlib stream incomplete'
        except Exception as exc:
            error = f'{type(exc).__name__}: {exc}'
        rows.append((index, info.file_size, expanded, error))
        if n % 25 == 0:
            print(f'Processed {n}/{len(infos)} in {time.monotonic()-start:.0f}s', flush=True)
    names = {r[0] for r in rows}
    missing = [i for i in range(378) if i not in names]
    good = [r for r in rows if not r[3]]
    lines = [
        'Super Smash Flash 2 Beta 1.4.0.1 original DAT archive size analysis',
        'Generated on temporary GitHub Actions runner. No game content included.',
        'Important: expanded asset size does not equal live Ruffle RAM usage.',
        f'Found {len(rows)} DAT files; successful decompressions: {len(good)}; failures: {len(rows)-len(good)}',
        'Missing numbers (0..377): ' + ', '.join(map(str, missing)),
        f'Total DAT file bytes: {sum(r[1] for r in rows):,}',
        f'Total decompressed bytes (successfully decoded only): {sum(r[2] for r in good):,}',
        f'Decompressed total: {sum(r[2] for r in good)/1048576:.2f} MiB',
        '', 'Largest 30 decompressed DAT files:'
    ]
    for i, c, e, error in sorted(good, key=lambda r:r[2], reverse=True)[:30]:
        lines.append(f'DAT{i}.ssf: stored={c/1048576:.2f} MiB -> decoded={e/1048576:.2f} MiB')
    lines.extend(['', 'Errors:'])
    for i, c, e, error in rows:
        if error:
            lines.append(f'DAT{i}.ssf: {error}')
    out.write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print('\n'.join(lines[:9]), flush=True)
    print(f'Report written to {out}', flush=True)
