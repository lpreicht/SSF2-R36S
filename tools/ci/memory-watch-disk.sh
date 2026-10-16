#!/usr/bin/env bash
# Diagnostic sampler for separate disk-backed SSF2 test only.
set -u
PID="${1:?missing PID}"
OUTPUT="${2:?missing logfile}"
{
  printf 'Disk cache test memory diagnostics for PID=%s\n' "$PID"
  printf 'Sampling every 2 seconds; KiB unless noted\n'
  printf 'Swaps:\n'
  cat /proc/swaps 2>/dev/null || true
  printf 'UTC | VmRSS VmHWM VmSwap VmSize RssAnon RssFile RssShmem | MemAvailable SwapFree | write_bytes read_bytes | oom_score\n'
  while kill -0 "$PID" 2>/dev/null && [[ -r "/proc/$PID/status" ]]; do
    read -r rss hwm swap vsz anon file shmem < <(awk '
      /^VmRSS:/ {rss=$2}
      /^VmHWM:/ {hwm=$2}
      /^VmSwap:/ {swap=$2}
      /^VmSize:/ {vsz=$2}
      /^RssAnon:/ {anon=$2}
      /^RssFile:/ {file=$2}
      /^RssShmem:/ {shmem=$2}
      END {print rss+0,hwm+0,swap+0,vsz+0,anon+0,file+0,shmem+0}
    ' "/proc/$PID/status" 2>/dev/null)
    read -r avail swapfree < <(awk '
      /^MemAvailable:/ {a=$2}
      /^SwapFree:/ {s=$2}
      END {print a+0,s+0}
    ' /proc/meminfo 2>/dev/null)
    read -r writes reads < <(awk '
      /^write_bytes:/ {w=$2}
      /^read_bytes:/ {r=$2}
      END {print w+0,r+0}
    ' "/proc/$PID/io" 2>/dev/null)
    score=$(cat "/proc/$PID/oom_score" 2>/dev/null || echo NA)
    printf '%s | %s %s %s %s %s %s %s | %s %s | %s %s | %s\n' \
      "$(date -u '+%H:%M:%S')" "$rss" "$hwm" "$swap" "$vsz" "$anon" "$file" "$shmem" \
      "$avail" "$swapfree" "$writes" "$reads" "$score"
    sleep 2
  done
  printf 'Sampler stopped at %s UTC\n' "$(date -u '+%H:%M:%S')"
} > "$OUTPUT" 2>&1
