#!/usr/bin/env bash
# Isolated, unverified memory experiment for Super Smash Flash 2 Beta 1.4.0.1.
# Never overwrite the existing Super Smash Flash 2 port or game assets.
set -u
PORTS="$(cd -- "$(dirname -- "$0")" && pwd)"
TEST="$PORTS/ssf2-r36s-memory-test"
GAME="$PORTS/ssf2-r36s/game/SSF2Portable.swf"
BIN="$TEST/ruffle-arm64-gles2-owned-fws-UNTESTED"
LOGDIR="$TEST/logs"
mkdir -p "$LOGDIR" || exit 1
LOG="$LOGDIR/last-run.log"
run() {
  printf 'SSF2 Beta 1.4.0.1 isolated Ruffle owned-FWS GLES2 test\n'
  printf 'Date UTC: %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  printf 'Kernel: %s\n' "$(uname -a)"
  printf 'Original SWF: %s\n' "$GAME"
  if [[ ! -f "$GAME" ]]; then
    echo "ERROR: SSF2Portable.swf not found in original game directory"
    return 2
  fi
  if [[ ! -d "$PORTS/ssf2-r36s/game/data" ]]; then
    echo "ERROR: original data/ folder not found"
    return 2
  fi
  if [[ ! -f "$BIN" ]]; then
    echo "ERROR: experimental ARM64 binary missing"
    return 3
  fi
  chmod +x "$BIN" 2>/dev/null || true
  if command -v ldd >/dev/null 2>&1; then
    echo "Dynamic library check (missing dependencies are diagnostic):"
    ldd "$BIN" 2>&1 || true
  fi
  cd "$TEST" || return 4
  export MALLOC_ARENA_MAX=1
  export RUST_BACKTRACE=1
  export RUST_LOG=info
  export SDL_GAMECONTROLLERCONFIG='190000004b4800000011000000010000,GO-Super Gamepad,x:b2,a:b1,b:b0,y:b3,back:b12,start:b13,dpleft:b10,dpdown:b9,dpright:b11,dpup:b8,leftshoulder:b4,lefttrigger:b6,rightshoulder:b5,righttrigger:b7,leftstick:b14,rightstick:b15,leftx:a0,lefty:a1,rightx:a2,righty:a3,platform:Linux,'
  echo "Starting GLES2 memory experiment in silent low quality mode"
  "$BIN" "$GAME" -Q low --no-audio &
  pid=$!
  echo "Process PID: $pid"
  if [[ -f "$TEST/memory-watch.sh" ]]; then
    bash "$TEST/memory-watch.sh" "$pid" "$LOGDIR/memory.log" &
    watch_pid=$!
  else
    watch_pid=''
  fi
  wait "$pid"
  status=$?
  if [[ -n "$watch_pid" ]]; then
    kill "$watch_pid" 2>/dev/null || true
    wait "$watch_pid" 2>/dev/null || true
  fi
  printf 'Ruffle exit code: %s\n' "$status"
  return "$status"
}
run >"$LOG" 2>&1
code=$?
echo "SSF2 memory experiment ended (code $code). Logs: $LOG"
exit "$code"
