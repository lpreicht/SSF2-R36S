# Experimental disk-backed SWF memory for SSF2 Beta 1.4.0.1

**Status:** source-level prototype, not a verified playable R36S port.

## Why the previous build still crashed

The first optimized ARM64 GLES2 build started SSF2 on a real R36S, but after about 85 seconds its resident RSS reached ~773 MiB and its zram swap use reached ~678 MiB. It was killed with exit code 137. Saving a single FWS memory copy was not enough.

## Prototype design

- New source patch: `tools/ci/patch_mmap_swf.py`, applied **after** `tools/ci/patch_owned_fws.py` to the exact pinned Ruffle fork.
- Feature: `ruffle_common/disk-mmap-experiment`, forwarded through `ruffle_core/disk-mmap-experiment`.
- **Off by default.** Even a build containing this feature never writes a SWF cache unless `SSF2_MMAP_CACHE_DIR` points to an existing writable folder.
- Only immutable SWF movie bytes of at least 128 KiB can be redirected to an anonymous file and read-only memory map.
- Hard 1 GiB cumulative per-process file-backed budget; any error causes the original in-memory storage to be kept for that resource. Original game DAT and SWF files are not modified.
- The temporary files are unlinked on Linux after creation. Their occupied disk blocks are released once the mapping/process is gone, including after a crash.
- The code flushes file writes before replacing the RAM buffer. This can be **very slow**, and the amount of data written may approach 1 GiB per startup.
- The separate AVM2 `ByteArray` buffers and decoded GPU bitmaps are **not** affected by this prototype. Real RAM reduction is unknown.

## Safety gates before a user test

1. Source-level Rust compile and mapping tests must succeed in GitHub CI.
2. Compile a separate ARM64/R36S GLES2 artifact. Keep the existing working port unchanged.
3. Test launcher must require **at least 2 GiB free on the actual game SD-card partition** before opting into disk backing, otherwise stop without disk writes.
4. Tell the user before installation that it may write **up to ~1 GiB during each start**, temporarily consume space, slow down drastically, and wear the SD card.
5. Collect `last-run.log` and `memory.log` from the separate test to measure actual improvement. Never claim it will reach 100% loading without that result.

## Build status (2026-10-16)

- [Source-level compile and unit tests: PASSED](https://github.com/lpreicht/SSF2-R36S/actions/runs/38830752904)
- [Native ARM64 GLES2 disk-backed Ruffle: PASSED](https://github.com/lpreicht/SSF2-R36S/actions/runs/38830752755) (build only; not verified to execute on ArkOS)
- [Isolated SD-card test ZIP: PASSED](https://github.com/lpreicht/SSF2-R36S/actions/runs/38831295062), artifact `SSF2-R36S-Disk-Test-UNTESTED`.

The new test menu item is `Super Smash Flash 2 Disk Test`. It sits alongside the existing port, uses the existing `ssf2-r36s/game/` files, and refuses to enable disk cache if the filesystem reports less than 2 GiB free. No sound in diagnostic mode. Real-device memory results are pending.

**Important:** File-backed pages still use RAM when accessed. Mapping alone cannot guarantee a lower active working set or playable speed on the R36S.


## On-device result: 37% loading, still OOM (2026-10-16)

The user tested the isolated disk cache build and visually observed the loading screen reach **37%**, versus 31% in the preceding tests.

Real ArkOS logs:
- Started 2026-10-16T00:51:23Z; last sample at 00:52:26Z (~63 seconds).
- GLES2 initialized; SWF version 40 (640×360, 30 FPS) loaded; controller recognized.
- Peak `VmHWM 803,600 KiB` (~784.8 MiB), versus prior owned-FWS test `791,860 KiB` (~773.3 MiB).
- Peak `VmSwap 691,620 KiB` (~675.4 MiB), versus prior ~678.4 MiB. `SwapFree` reached exactly **0 KiB**.
- Final exit: 137 / SIGKILL, strongly consistent with memory exhaustion. The OOM-killer was not directly logged.
- Prior `last-run.log` contains **no** `Disk-backed SWF mapped` lines, so whether any mmap succeeded remains **unconfirmed**. The old patch used `tracing::info!`, whereas the frontend initializes `env_logger` and does not necessarily have a tracing subscriber.

Engineering reaction:
- Do **not** infer that 37% means the cache demonstrably reduced RAM, because the memory measurements show no material benefit.
- New source patch logs each mmap success/failure directly on stderr, which the launcher collects.
- A dedicated `memory-watch-disk.sh` samples `RssAnon`, `RssFile`, `RssShmem`, and process `write_bytes` / `read_bytes`, besides existing RSS and zram swap.
- Only after confirming real file mappings and their size should we consider more disk-related changes. Never automatically increase cache budget or put original game files at risk.


## Diagnostics package built after the 37% test

The updated diagnostic-only package was built successfully by [GitHub Actions run #38832786630](https://github.com/lpreicht/SSF2-R36S/actions/runs/38832786630). Artifact: `SSF2-R36S-Disk-Test-UNTESTED`.

It changes **only diagnostic visibility**: the patched ARM64 runtime writes mmap success/failure messages directly to stderr (captured in `last-run.log`), and the included monitor logs anonymous vs file-backed RSS and per-process I/O in `memory.log`. It does **not** enlarge the 1 GiB disk cache or claim to fix OOM. Source compile/tests and ARM64 release build passed CI; actual benefit is unverified. A single on-device retest (with explicit SD write warning) is needed only if diagnosing whether disk cache actually ran.


## Confirmed second 37% test: cache active, no material RAM relief

A second hardware test on **2026-10-16 01:02:56–01:04:37 UTC** again stopped visually at **37%** and exited **137**.

This time the instrumented launcher explicitly confirmed **11 successful file-backed SWF maps** totaling **68,974,544 bytes (65.78 MiB)**. This is only **6.42% of the existing 1 GiB cumulative cache budget**, so raising that budget cannot address the bottleneck without changing which data is eligible for the cache.

Memory watcher results:
- VmHWM **808,340 KiB ≈ 789.4 MiB**; VmSwap **692,280 KiB ≈ 676.1 MiB**.
- System SwapFree fell to **0 KiB**, MemAvailable about **14 MiB**, followed by SIGKILL exit code 137.
- `RssAnon`/`RssFile`/`RssShmem` all reported 0 because these entries were not exposed by the old Linux 4.4 kernel's `/proc/<pid>/status`; **not** because true file-backed RSS is zero.
- `write_bytes` / `read_bytes` remained blank (unreadable/missing proc I/O fields, likely permission-dependent), so no reliable total disk writes can be derived from this watcher.
- No explicit kernel OOM-killer message; OOM is strongly indicated by full zram + exit 137.

**Engineering decision:** Pause this disk-backed SwfMovie cache path. It is technically verified but only covers ~66 MiB of movie bytes before the load abort, while the process consumes ~1.5 GiB resident+swap. Do **not** increase swap or cache sizes or request repeated retests of identical code. Next investigate large **AVM2 ByteArray buffers** and **decoded BitmapData CPU pixels**, both excluded from this cache. Ruffle's ordinary `BitmapCharacter` is already lazily decoded, so indiscriminately adding lazy bitmap decoding is not a new fix without locating the actual allocations. Any new candidate needs measurable allocation evidence and must preserve game behaviors and ARM64 compatibility.

