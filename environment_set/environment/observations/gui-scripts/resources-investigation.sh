#!/usr/bin/env bash
set -euo pipefail
: "${PDF_ANALYZER_HOME:?Run this script in PDF Analyzer}"
: "${PDF_RUN_DIR:?Missing run output path}"
for ((number = 1; number <= 15; number++)); do
printf -v tool ’pr%02d’ "$number"
printf ’Collecting resources for %s\n’ "$tool" >&2
python3 "$PDF_ANALYZER_HOME/lab.py" resources --tool "$tool" \
> "$PDF_RUN_DIR/${tool}-resources.tsv"
done
