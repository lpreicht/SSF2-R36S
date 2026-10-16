#!/usr/bin/env bash
# SIDE-BY-SIDE R36S SSF2 Beta 1.4.0.1 experimental disk-backed SWF loader.
# This writes up to 1 GiB to temporary files on the EASYROMS SD filesystem.
# DO NOT install over the existing Super Smash Flash 2 port.
set -u
PORTS="$(cd -- "$(dirname -- "$0")" && pwd)"
TEST="$PORTS/ssf2-r36s-disk-test"
GAME="$PORTS/ssf2-r36s/game/SSF2Portable.swf"
BIN="$TEST/ruffle-arm64-gles2-diskcache-UNTESTED"
CACHE="$TEST/cache"
LOGDIR="$TEST/logs"
mkdir -p "$LOGDIR" || exit 1
LOG="$LOGDIR/last-run.log"
test_run() {
    printf 'SSF2 1.4.0.1 OPTIONAL DISK CACHE TEST\nDate UTC: %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    printf 'Kernel: %s\n' "$(uname -a)"
    printf 'Game: %s\nCache: %s\n' "$GAME" "$CACHE"
    if [[ ! -f "$GAME" || ! -d "$PORTS/ssf2-r36s/game/data" ]]; then
        echo 'ERROR: Existing official SSF2 1.4.0.1 game files not found.'
        return 2
    fi
    if [[ ! -f "$BIN" ]]; then
        echo 'ERROR: Compiled disk-cache runtime missing.'
        return 3
    fi
    mkdir -p "$CACHE" || return 4
    # Only enable the experimental cache when enough free SD space exists.
    # The runtime has an additional independent 1 GiB cumulative write limit.
    free_kib="$(df -Pk "$CACHE" 2>/dev/null | awk 'NR == 2 {print $4}')"
    if [[ ! "$free_kib" =~ ^[0-9]+$ ]]; then
        echo 'ERROR: Could not check free SD card capacity; refusing to write.'
        return 5
    fi
    printf 'Free SD capacity: %s KiB\n' "$free_kib"
    if (( free_kib < 2097152 )); then
        printf 'ERROR: Require at least 2 GiB free; refusing to write any cache.\n'
        return 6
    fi
    echo 'WARNING: THIS TEST MAY WRITE UP TO 1 GiB TO SD PER LAUNCH.'
    echo 'WARNING: EXTREMELY SLOW LOADING AND SD CARD WEAR ARE POSSIBLE.'
    echo 'Original SSF2 files and ArkOS settings are untouched.'
    chmod +x "$BIN" 2>/dev/null || true
    echo 'Shared libraries:'
    if command -v ldd >/dev/null 2>&1; then
        ldd "$BIN" 2>&1 || true
    fi
    export SSF2_MMAP_CACHE_DIR="$CACHE"
    export MALLOC_ARENA_MAX=1
    export RUST_BACKTRACE=1
    export RUST_LOG=info
    cd "$TEST" || return 7
    printf 'Mmap experiment: enabled; max 1 GiB cumulative SWF bytes\n'
    "$BIN" "$GAME" -Q low --no-audio &
    pid=$!
    echo "Ruffle PID: $pid"
    if [[ -f "$TEST/memory-watch.sh" ]]; then
        bash "$TEST/memory-watch.sh" "$pid" "$LOGDIR/memory.log" &
        watcher_pid=$!
    else
        watcher_pid=''
    fi
    wait "$pid"
    code=$?
    if [[ -n "$watcher_pid" ]]; then
        kill "$watcher_pid" 2>/dev/null || true
        wait "$watcher_pid" 2>/dev/null || true
    fi
    echo "Ruffle exit code: $code"
    return "$code"
}
test_run > "$LOG" 2>&1
code=$?
echo "SSF2 Disk Test exited $code. Log: $LOG"
exit "$code"
