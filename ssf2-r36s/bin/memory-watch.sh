#!/usr/bin/env bash
# Monitor a running Ruffle process without root permissions.
# Usage: memory-watch.sh PID /path/to/log
set -u
PID="${1:?process pid missing}"
OUT="${2:?output file missing}"
{
  printf 'Memory diagnostic for Ruffle PID=%s\n' "$PID"
  printf 'Sampling interval: 2 seconds\n'
  printf 'Kernel: %s\n' "$(uname -r)"
  printf 'Swaps:\n'
  cat /proc/swaps 2>/dev/null || true
  printf 'TimeUTC | VmRSS_kB VmHWM_kB VmSwap_kB VmSize_kB | MemAvailable_kB SwapFree_kB | oom_score\n'
  while kill -0 "$PID" 2>/dev/null; do
    if [[ ! -r "/proc/$PID/status" ]]; then
      break
    fi
    read -r rss hwm swap vsz < <(awk '
      /^VmRSS:/  {rss=$2}
      /^VmHWM:/  {hwm=$2}
      /^VmSwap:/ {swp=$2}
      /^VmSize:/ {vsz=$2}
      END {print rss+0, hwm+0, swp+0, vsz+0}
    ' "/proc/$PID/status" 2>/dev/null)
    read -r avail swapfree < <(awk '
      /^MemAvailable:/ {a=$2}
      /^SwapFree:/ {s=$2}
      END {print a+0, s+0}
    ' /proc/meminfo 2>/dev/null)
    score=$(cat "/proc/$PID/oom_score" 2>/dev/null || echo NA)
    printf '%s | %s %s %s %s | %s %s | %s\n' \
      "$(date -u '+%H:%M:%S')" "$rss" "$hwm" "$swap" "$vsz" "$avail" "$swapfree" "$score"
    sleep 2
  done
  printf 'Monitor finished at %s\n' "$(date -u '+%H:%M:%S')"
} > "$OUT" 2>&1
