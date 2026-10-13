# Super Smash Flash 2 for R36S (ArkOS) — TEST BUILD

> **Experimental:** This is a first test build, **not** a confirmed working or optimized port. SSF2 1.4.0.1 has not yet been verified on a real R36S in this setup.

A dedicated **Super Smash Flash 2** game entry in ArkOS Ports. It uses an ARM64 Ruffle runtime for Flash, **not** the x86 Windows executable or Adobe AIR. No original SSF2 game files are included.

## Installation

1. Go to **Actions → Build test installer → latest successful run**. Download the `SSF2-R36S-test` artifact and extract the `SSF2-R36S-test.zip` inside.
2. Copy the ZIP's two entries into the `ports` folder of the `EASYROMS` partition on your R36S SD card.
3. From your legally downloaded **SSF2 Beta 1.4.0.1 Windows Portable** copy only:
   - `SSF2Portable.swf` → `EASYROMS/ports/ssf2-r36s/game/SSF2Portable.swf`
   - the whole `data` directory → `EASYROMS/ports/ssf2-r36s/game/data/`
4. Copy the **entire original `data` directory** without renaming or converting anything. Numbered DAT files do not necessarily have to form an uninterrupted sequence; the launcher reports absent numbers but does not block the game.
5. Open **Ports → Super Smash Flash 2** on your R36S. If it fails to run, send `ssf2-r36s/logs/last-run.log` and report how far it gets.

Expected SD-card structure:

```text
EASYROMS/ports/
├── Super Smash Flash 2.sh
└── ssf2-r36s/
    ├── rufflesa                  (ARM64 Ruffle runtime, local path patch)\n    ├── bin/console_detect        (local 640x480 compatibility helper)
    ├── keymap/SSF2Portable.cfg
    ├── game/
    │   ├── SSF2Portable.swf      (you supply)
    │   └── data/
    │       ├── DAT0.ssf         (you supply)
    │       └── ... DAT377.ssf
    └── logs/last-run.log         (generated)
```

The launcher reports missing DAT numbers without treating them as fatal, runs Ruffle with low-quality rendering and logs startup errors. Ruffle's bundled ARM64 binary originally contains a hardcoded path to \`/usr/local/bin/console_detect\`; the GitHub Actions build makes a size-preserving path substitution to a local compatibility helper under \`ssf2-r36s/bin/\`. This is a patched binary: it does not require remounting ArkOS or changing system files. It does **not** remount the root filesystem or change `/usr/local/bin`.

## Controls (provisional)

A: attack (P), B: special (O), X/R: grab (U), Y/L: shield (I).
The third-party R36S Ruffle build reports `Select + A` as the D-pad WASD toggle (needed for SSF2 Player 1), `Select + X` as mouse mode for menus, and `Select + Start` to exit. Buttons and menu interaction still need verification on the device.

## Test build: loading-screen exit 137 (2026-10-13)

The 1.4.0.1 loading screen reached ~30% but Ruffle was killed with exit code 137 (SIGKILL) after ~78 seconds. **This is not proof of OOM.** Logs also showed repeated ALSA underrun errors. To diagnose:

- This experimental build launches with **`--no-audio`** and low graphics quality. Sound is deliberately off for this one test, not removed from the intended final port.
- `ssf2-r36s/logs/memory.log` samples Ruffle process RSS/peak RAM, swap, and system available RAM every two seconds.
- `ssf2-r36s/logs/last-run.log` includes the Ruffle exit code and Linux kernel OOM-kill counter before and after.
- After testing, **send both log files**, and report loading percentage and elapsed time. The game files do not need to be uploaded again.
- If this build starts but no sound plays, that is expected. If it rejects `--no-audio`, the log should say so, and we can change that flag.

The upstream Ruffle project has open SSF2 loading and performance issues: https://github.com/ruffle-rs/ruffle/issues/21876 and https://github.com/ruffle-rs/ruffle/issues/24032 .

## Current limitations

Ruffle support for advanced ActionScript 3 and loading 378 external assets is not guaranteed on this device. R36S RAM is about 1 GB, and upstream Ruffle has reported SSF2 memory/performance and rendering problems. There is no confirmed playable frame rate for SSF2 Beta 1.4.0.1 on this hardware.

## Credits and copyrights

SSF2 © its respective rights holders. Obtain the game at https://www.supersmashflash.com/play/ssf2/downloads/ .

Patched ARM64 Ruffle runtime obtained at packaging time from https://github.com/Cristiangc67/ruffle-r36s-darkos (built upon https://github.com/ruffle-rs/ruffle, https://github.com/aweigit/ruffle-miyooflip and lcdyk0517/arkos4clone). Respect their open-source license notices when redistributing. This project is unofficial and unaffiliated.
