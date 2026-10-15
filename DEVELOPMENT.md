# SSF2 1.4.0.1 — memory engineering notes

Last updated: 2026-10-16

## Device-grounded constraint
Actual R36S / ArkOS logs: 897 MiB-class RAM, 768 MiB zram; loading reaches ~31%, then SIGKILL 137. Peak resident usage ~789 MiB, swap ~675 MiB, free swap goes to zero. Disabling sound did **not** resolve the kill. No evidence that seven skipped DAT indexes are errors; the official ZIP is identical.

## Verified official game data
[GitHub-only asset inspection](https://github.com/lpreicht/SSF2-R36S/actions/runs/38821717604) processed all 371 DAT files; each starts with an external ZLIB wrapper and contains a SWF FWS signature in the first 64KiB of unpacked content.
- Original compressed DAT total: 917,452,511 bytes.
- Outer ZLIB expanded total: 968,270,739 bytes (~923.4 MiB).
- The seven absent DAT indexes are absent from the official distribution too.
**Caution:** These totals are aggregate file data, not live Ruffle allocations. No conclusion about exact memory duplication counts follows from file sizes alone.

## Actual Ruffle source audit
Current game launcher uses a pre-built ARM64 Ruffle binary. Its lineage is [aweigit/ruffle-miyooflip](https://github.com/aweigit/ruffle-miyooflip), which was pinned at commit `2d8383792ad9ca984d14a2787858151ff03e4434` for build experiments.

At that source commit:
- `core/src/avm2/globals/flash/display/loader.rs` in `load_bytes`: `arg0.as_bytearray().unwrap().bytes().to_vec()` unconditionally clones the SWF byte buffer passed through ActionScript `Loader.loadBytes`.
- `core/common/src/tag_utils.rs` in `SwfMovie::from_data`: calls `swf::read::decompress_swf(swf_data)`, creating a separate decompressed buffer.
- `swf/src/read.rs` in `decompress_swf`: allocates a fresh Vec even for uncompressed FWS streams, and copies the body from its source.
- `ByteArrayStorage` itself owns a Vec. Transferring that Vec from the AVM2 `ByteArray` would change Flash-visible semantics if ActionScript retains the original object. A naïve `mem::take`/swap is NOT a safe fix.

This creates transient copies along some load paths. **It does not prove** that those copies are the source of the sustained 1.4+ GiB memory pressure; for a single resource, the largest recorded uncompressed DAT is ~22.4 MiB. Optimizing transient copies alone is not expected to guarantee playability.

## Engineering milestone before attempting a memory optimization
A [GitHub Actions source build](https://github.com/lpreicht/SSF2-R36S/actions/runs/38822304663) was added to check that the pinned handheld Ruffle core compiles unmodified first. This is **not** an ARM64 port release. If it succeeds, a dedicated source patch and tests can be developed from a reproducible baseline; cross-compiling the modified ARM64 binary for ArkOS is another separate requirement.

A meaningful patch must (1) preserve `ByteArray` observable behavior and loaded SWF correctness, (2) show memory improvement in a reproducible test, and (3) be compiled for the R36S ARM64/ArkOS runtime before giving the user another install package.

## No unjustified quick fixes
Do not silently replace the requested SSF2 Beta 1.4.0.1 with 0.8b; do not suggest another texture-quality toggle as a memory fix; do not claim that adding disk swap yields a playable full game; do not package copyrighted game data.
