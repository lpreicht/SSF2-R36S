# Super Smash Flash 2 for R36S (ArkOS) — TEST BUILD

> **Experimental:** This is a first test build, **not** a confirmed working or optimized port. SSF2 1.4.0.1 has not yet been verified on a real R36S in this setup.

A dedicated **Super Smash Flash 2** game entry in ArkOS Ports. It uses an ARM64 Ruffle runtime for Flash, **not** the x86 Windows executable or Adobe AIR. No original SSF2 game files are included.

## Installation

1. Go to **Actions → Build test installer → latest successful run**. Download the `SSF2-R36S-test` artifact and extract the `SSF2-R36S-test.zip` inside.
2. Copy the ZIP's two entries into the `ports` folder of the `EASYROMS` partition on your R36S SD card.
3. From your legally downloaded **SSF2 Beta 1.4.0.1 Windows Portable** copy only:
   - `SSF2Portable.swf` → `EASYROMS/ports/ssf2-r36s/game/SSF2Portable.swf`
   - the whole `data` directory → `EASYROMS/ports/ssf2-r36s/game/data/`
4. Check that the `data` directory contains `DAT0.ssf` through `DAT377.ssf` (378 separate data files). **Do not rename or convert them.**
5. Open **Ports → Super Smash Flash 2** on your R36S. If it fails to run, send `ssf2-r36s/logs/last-run.log` and report how far it gets.

Expected SD-card structure:

```text
EASYROMS/ports/
├── Super Smash Flash 2.sh
└── ssf2-r36s/
    ├── rufflesa                  (ARM64 runtime provided by Actions artifact)
    ├── keymap/SSF2Portable.cfg
    ├── game/
    │   ├── SSF2Portable.swf      (you supply)
    │   └── data/
    │       ├── DAT0.ssf         (you supply)
    │       └── ... DAT377.ssf
    └── logs/last-run.log         (generated)
```

The launcher verifies all 378 data files, runs Ruffle with low-quality rendering and logs startup errors. It does **not** remount the root filesystem or change `/usr/local/bin`.

## Controls (provisional)

A: attack (P), B: special (O), X/R: grab (U), Y/L: shield (I).
The third-party R36S Ruffle build reports `Select + A` as the D-pad WASD toggle (needed for SSF2 Player 1), `Select + X` as mouse mode for menus, and `Select + Start` to exit. Buttons and menu interaction still need verification on the device.

## Current limitations

Ruffle support for advanced ActionScript 3 and loading 378 external assets is not guaranteed on this device. R36S RAM is about 1 GB, and upstream Ruffle has reported SSF2 memory/performance and rendering problems. There is no confirmed playable frame rate for SSF2 Beta 1.4.0.1 on this hardware.

## Credits and copyrights

SSF2 © its respective rights holders. Obtain the game at https://www.supersmashflash.com/play/ssf2/downloads/ .

ARM64 Ruffle runtime obtained at packaging time from https://github.com/Cristiangc67/ruffle-r36s-darkos (built upon https://github.com/ruffle-rs/ruffle, https://github.com/aweigit/ruffle-miyooflip and lcdyk0517/arkos4clone). Respect their open-source license notices when redistributing. This project is unofficial and unaffiliated.
