#!/usr/bin/env bash
# SSF2 for R36S / ArkOS - first experimental launcher
set -u
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
BASE="$ROOT/ssf2-r36s"
BIN="$BASE/rufflesa"
GAME="$BASE/game/SSF2Portable.swf"
ASSETS="$BASE/game/data"
LOGDIR="$BASE/logs"
mkdir -p "$LOGDIR" || exit 1
LOG="$LOGDIR/last-run.log"
run() {
  printf 'SSF2 R36S experimental launcher\n'
  printf 'Date: %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || echo unknown)"
  printf 'System: %s\n' "$(uname -m 2>/dev/null || echo unknown)"
  printf 'Base: %s\n' "$BASE"
  if [[ ! -f "$GAME" ]]; then
    printf 'ERROR: Missing %s\n' "$GAME"
    return 2
  fi
  if [[ ! -d "$ASSETS" ]]; then
    printf 'ERROR: Missing data folder: %s\n' "$ASSETS"
    return 2
  fi
  # The original game may omit some DAT numbers intentionally.
  # A contiguous range from 0 to 377 is NOT proof that every number exists.
  missing=0
  for ((i=0; i<=377; i++)); do
    if [[ ! -f "$ASSETS/DAT${i}.ssf" ]]; then
      ((missing+=1))
      printf 'NOTICE: DAT${i}.ssf not present\n'
    fi
  done
  present=$(find "$ASSETS" -maxdepth 1 -type f -name 'DAT*.ssf' | wc -l)
  printf 'Data files present: %s; absent numbers in DAT0..DAT377: %s\n' "$present" "$missing"
  if (( missing > 0 )); then
    printf 'NOTICE: Starting anyway; missing numbers may be normal in the official distribution.\n'
  fi
  if [[ ! -f "$BIN" ]]; then
    printf 'ERROR: ARM Ruffle runtime missing: %s\n' "$BIN"
    return 3
  fi
  chmod +x "$BIN" 2>/dev/null || true
  if [[ ! -x "$BIN" ]]; then
    printf 'ERROR: ARM Ruffle runtime not executable: %s\n' "$BIN"
    return 3
  fi
  # Ruffle looks for custom keymaps relative to its working directory.
  # Use the engine directory; the game file path is still absolute.
  cd "$BASE" || return 4
  # Ruffle's R36S build expects console_detect. Use a local, harmless
  # 640x480 shim rather than modifying /usr/local/bin or remounting /.
  if [[ -f "$BASE/bin/console_detect" ]]; then
    chmod +x "$BASE/bin/console_detect" 2>/dev/null || true
  fi
  export PATH="$BASE/bin:$PATH"
  if ! command -v console_detect >/dev/null 2>&1; then
    printf 'ERROR: console_detect helper missing. Reinstall updated test package.\n'
    return 5
  fi
  printf 'console_detect: %s\n' "$(command -v console_detect)"
  printf 'Screen resolution: %s\n' "$(console_detect 2>&1)"
  printf 'Working directory: %s\n' "$PWD"
  if [[ -f "keymap/SSF2Portable.cfg" ]]; then
    printf 'Custom keymap: found\n'
  else
    printf 'WARNING: custom keymap missing at %s/keymap/SSF2Portable.cfg\n' "$BASE"
  fi
  export SDL_GAMECONTROLLERCONFIG='190000004b4800000011000000010000,GO-Super Gamepad,x:b2,a:b1,b:b0,y:b3,back:b12,start:b13,dpleft:b10,dpdown:b9,dpright:b11,dpup:b8,leftshoulder:b4,lefttrigger:b6,rightshoulder:b5,righttrigger:b7,leftstick:b14,rightstick:b15,leftx:a0,lefty:a1,rightx:a2,righty:a3,platform:Linux,'
  export RUST_BACKTRACE=1
  printf 'Starting Ruffle with low quality setting\n'
  "$BIN" "$GAME" -Q low
  status=$?
  printf '\nRuffle exit code: %s (does not prove gameplay succeeded)\n' "$status"
  return "$status"
}
run >"$LOG" 2>&1
status=$?
if (( status != 0 )); then
  printf 'SSF2 start failed (code %s). See %s\n' "$status" "$LOG" >&2
fi
exit "$status"
