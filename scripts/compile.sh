#!/usr/bin/env bash
# Compile a resume .tex and report compile status + page count.
# Usage: scripts/compile.sh <path/to/resume.tex> [max_pages]
#   max_pages defaults to 1. Pass 2 for the RS/academic-CV exception (CONSTRAINTS §2).
# Exit 0 iff it compiled AND page count is between 1 and max_pages (gate check).
set -uo pipefail

tex="${1:?usage: compile.sh <path/to/resume.tex> [max_pages]}"
maxpages="${2:-1}"
dir="$(dirname "$tex")"
base="$(basename "$tex" .tex)"

pdflatex -interaction=nonstopmode -halt-on-error -output-directory="$dir" "$tex" >/dev/null 2>&1
status=$?
log="$dir/$base.log"

pages=$(python3 - "$log" <<'PY'
import re, sys
try:
    log = open(sys.argv[1], 'rb').read().decode('latin-1')
    m = re.search(r'Output written on .*?\((\d+) page', log.replace('\n', ''))
    print(m.group(1) if m else 'UNKNOWN')
except Exception:
    print('UNKNOWN')
PY
)

if [ $status -eq 0 ]; then
  echo "COMPILE: ok  ($dir/$base.pdf)"
else
  echo "COMPILE: FAILED  (see $log)"
fi
echo "PAGES:   $pages  (limit: $maxpages)"

[ $status -eq 0 ] && [[ "$pages" =~ ^[0-9]+$ ]] && [ "$pages" -ge 1 ] && [ "$pages" -le "$maxpages" ]
