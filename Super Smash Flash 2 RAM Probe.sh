#!/usr/bin/env bash
# SSF2 Beta 1.4.0.1 diagnostic probe, without experimental disk caching.
# Separate port entry; original game files are used read-only.
set -u
PORTS="$(cd -- "$(dirname -- "$0")" && pwd)"
TEST="$PORTS/ssf2-r36s-ram-probe"
GAME="$PORTS/ssf2-r36s/game/SSF2Portable.swf"
BIN="$TEST/ruffle-arm64-ramprobe-UNTESTED"
LOGDIR="$TEST/logs"
mkdir -p "$LOGDIR" || exit 1
LOG="$LOGDIR/last-run.log"

run_probe() {
  echo "SSF2 Beta 1.4.0.1 RAM ATTRIBUTION PROBE (NO DISK CACHE)"
  printf 'Date UTC: %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  uname -a
  printf 'Game: %s\nExecutable: %s\n' "$GAME" "$BIN"
  if [[ ! -f "$GAME" || ! -d "$PORTS/ssf2-r36s/game/data" ]]; then
    echo "ERROR: Original game SWF/data directory is missing."
    return 2
  fi
  if [[ ! -f "$BIN" ]]; then
    echo "ERROR: Diagnostic ARM64 binary is missing."
    return 3
  fi
  chmod +x "$BIN" 2>/dev/null || true
  if command -v ldd >/dev/null 2>&1; then
    ldd "$BIN" 2>&1 || true
  fi
  cd "$TEST" || return 4
  unset SSF2_MMAP_CACHE_DIR
  export MALLOC_ARENA_MAX=1
  export RUST_BACKTRACE=1
  export RUST_LOG=info
  echo "[SSF2-RAM] All counters are cumulative allocation events, NOT live retained bytes."
  echo "Ruffle will run with sound off and low stage quality."
  "$BIN" "$GAME" -Q low --no-audio &
  pid=$!
  echo "Ruffle process PID: $pid"
  if [[ -f "$TEST/memory-watch.sh" ]]; then
    bash "$TEST/memory-watch.sh" "$pid" "$LOGDIR/memory.log" &
    watcher=$!
  else
    watcher=''
  fi
  wait "$pid"
  code=$?
  if [[ -n "$watcher" ]]; then
    kill "$watcher" 2>/dev/null || true
    wait "$watcher" 2>/dev/null || true
  fi
  printf 'Exit code: %s\n' "$code"
  return "$code"
}
run_probe >"$LOG" 2>&1
code=$?
echo "RAM probe ended (code $code). Logs: $LOG"
exit "$code"
