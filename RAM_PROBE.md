# SSF2 1.4.0.1: ARM64 RAM attribution experiment

## Why this experiment

Two distinct R36S disk-backed builds both reached about **37%** loading, then were killed with exit 137 after exhausting the available zram swap. The latest confirmed hardware run showed **11 successful mmap allocations totaling 68,974,544 bytes (65.8 MiB)**, while peak resident usage approached 789 MiB and swap approached 676 MiB. Increasing the 1 GiB disk-mmap budget could not materially affect that result, because less than 7% of the budget was used.

The pinned Ruffle fork already lazily decodes embedded bitmap characters, therefore claiming that simply introducing lazy bitmaps is a new solution would be incorrect.

## What was implemented

- [`tools/ci/patch_ram_probe.py`](tools/ci/patch_ram_probe.py) modifies the pinned Ruffle source in temporary GitHub Actions build checkouts only.
- ByteArray event categories: `ByteArray.import`, `ByteArray.growth`, `ByteArray.inflate`.
- Graphic asset categories: `SWF.Bitmap.compressed`, `SWF.Bitmap.decoded_rgba`, `BitmapData.CPU_RGBA`.
- Events are emitted as `[SSF2-RAM]` to stderr in the existing ArkOS `last-run.log`. Output is rate-limited to allocations >=4 MiB or crossing 16 MiB cumulative increments for each category.
- The counters describe **cumulative observed allocations / expansions** and are **not** live heap allocation, nor precise GPU memory, nor unique asset storage. For instance, an imported ByteArray may be counted again if its storage is swapped, and decoded bitmap sizes are logical 4-byte/pixel estimates.
- Existing `memory.log` simultaneously measures the operating system process's VmRSS/VmHWM/VmSwap and system SwapFree.
- Neither the cache patch nor `SSF2_MMAP_CACHE_DIR` is enabled. The isolated launcher explicitly unsets the cache environment variable.
- Does not include or alter copyrighted game files. Main SSF2 launcher remains untouched.

## Expected diagnostic use

1. Confirm that the binary launches on R36S.
2. Let SSF2 Beta 1.4.0.1 run **once** until the usual load abort.
3. Inspect each `[SSF2-RAM]` category with the VmRSS/SwapFree curve, and determine whether large byte arrays or bitmap pixels are actually being materialized at the fatal loading stage.
4. If neither accounts for the pressure, profile other Rust memory allocations or retained AVM2/GC objects, rather than committing more blind tweaks.

## Build status

- [Source check and SWF tests](https://github.com/lpreicht/SSF2-R36S/actions/runs/38834650780): **passed**.
- [ARM64 source build](https://github.com/lpreicht/SSF2-R36S/actions/runs/38834712479): started; its result must be checked separately.
- The standalone test uses the alternate `Super Smash Flash 2 RAM Probe.sh` launcher and folder `ssf2-r36s-ram-probe`. No SD-backed SWF cache or extra swap is used.

Even a successful ARM64 build does **not** establish that the full game fits in the R36S's 1 GiB RAM.
