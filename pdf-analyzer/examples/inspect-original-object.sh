#!/usr/bin/env bash
set -euo pipefail

: "${PDF_DATASET_DIR:?Run this script in PDF Analyzer}"
: "${PDF_RUN_DIR:?Missing run output path}"

# Change these values after reading a resource row's original reference.
document="GGGXC"
object_reference="28,0"  # object number,generation; equivalent to 28 0 R

pdf="$(find "$PDF_DATASET_DIR" -type f -iname "${document}*.pdf" -print -quit)"
if [[ -z "$pdf" ]]; then
    printf 'PDF not found for %s\n' "$document" >&2
    exit 1
fi

# Store the original definition without rewriting or converting the PDF.
raw="$PDF_RUN_DIR/object-definition.txt"
status="ok"
if qpdf --show-object="$object_reference" "$pdf" > "$raw"; then
    :
else
    code=$?
    if [[ "$code" -eq 3 ]]; then
        status="qpdf warning; inspect stderr"
    else
        printf 'Object inspection failed (exit %s).\n' "$code" >&2
        exit "$code"
    fi
fi

# Flatten tabs/newlines so the definition occupies one TSV cell.
definition="$(tr '\t\r\n' '   ' < "$raw")"
printf 'document\tobject_reference\tstatus\tdefinition\n'
printf '%s\t%s\t%s\t%s\n' "$document" "$object_reference" "$status" "$definition"
