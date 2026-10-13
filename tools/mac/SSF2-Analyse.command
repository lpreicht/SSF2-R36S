#!/bin/bash
# macOS double-click helper - choose SSF2 1.4.0.1's original data folder.
cd "$(dirname "$0")" || exit 1
echo "SSF2 1.4.0.1 resource analysis (read-only)"
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 was not found. Install Python 3 on your Mac."
  read -r -p "Press Return to close..."
  exit 1
fi
DATA_DIR="$(osascript -e 'POSIX path of (choose folder with prompt "Choose the SSF2 1.4.0.1 data folder:")' 2>/dev/null)"
if [[ -z "$DATA_DIR" ]]; then
  echo "Canceled."
  exit 0
fi
python3 ./analyze_ssf2.py "$DATA_DIR"
status=$?
echo ""
echo "Please upload SSF2-R36S-resource-report.txt from the parent of the data folder."
read -r -p "Press Return to close..."
exit "$status"
