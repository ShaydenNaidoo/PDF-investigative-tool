#!/usr/bin/env bash
set -euo pipefail

: "${PDF_ANALYZER_HOME:?Run this script in PDF Analyzer}"
: "${PDF_RUN_DIR:?Missing run output path}"

tools=(
    pr01 pr02 pr03 pr04 pr05
    pr06 pr07 pr08 pr09 pr10
    pr11 pr12 pr13 pr14 pr15
)

for tool in "${tools[@]}"; do
    printf 'Collecting resources for %s\n' "$tool" >&2

    python3 "$PDF_ANALYZER_HOME/lab.py" resources \
        --tool "$tool" \
        > "$PDF_RUN_DIR/${tool}-resources.tsv"
done

printf 'Finished collecting Part 1 resource evidence.\n' >&2
