#!/usr/bin/env bash
set -euo pipefail

: "${PDF_ANALYZER_HOME:?Run this script in PDF Analyzer}"
: "${PDF_RUN_DIR:?Missing run output path}"

# One table per tool; overlapping exemplar IDs remain in their respective sets.
for ((number = 1; number <= 15; number++)); do
    printf -v tool 'pr%02d' "$number"
    printf 'Investigating %s\n' "$tool" >&2
    python3 "$PDF_ANALYZER_HOME/lab.py" numbering --tool "$tool" \
        > "$PDF_RUN_DIR/${tool}-numbering.tsv"
done
