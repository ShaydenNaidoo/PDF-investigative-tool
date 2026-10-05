#!/usr/bin/env bash

set -u

OBS="${PDF_OBSERVATIONS_DIR:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)}"
DATASET="${PDF_DATASET_DIR:-$(cd -- "$OBS/../../master-gdc-gdcdatasets-2020445568-2020445568/lcwa_gov_pdf_data/data" && pwd)}"

RESULTS="$OBS/part1-test-results"
QDFDIR="$RESULTS/qdf"

RAW="$RESULTS/all-resources.tsv"
ERRORS="$RESULTS/qpdf-errors.txt"

for required in qpdf awk sed grep find sort uniq column; do
    command -v "$required" >/dev/null 2>&1 || { echo "ERROR: $required is required."; exit 1; }
done
[[ -d "$DATASET" && -f "$OBS/all" ]] || { echo "ERROR: Dataset or observations/all is missing."; exit 1; }

mkdir -p "$QDFDIR"

: > "$ERRORS"

printf "document\tresource_type\tresource_name\tprefix\tnumber\tobject\n" > "$RAW"


find_pdf()
{
    local id="$1"

    find "$DATASET" \
        -type f \
        -iname "${id}*.pdf" \
        -print \
        -quit
}


extract_resources()
{
    local document="$1"
    local qdf="$2"

    awk -v document="$document" '

    BEGIN {
        category=""
        depth=0
    }

    function prefix_of(name, result) {
        result=name
        sub(/[0-9]+$/, "", result)
        return result
    }

    function number_of(name, result) {
        result=name

        if (match(result, /[0-9]+$/)) {
            return substr(result, RSTART, RLENGTH)
        }

        return ""
    }

    # --------------------------------------------------------
    # Detect beginning of resource dictionaries
    # --------------------------------------------------------

    /^[[:space:]]*\/Font[[:space:]]*<</ {
        category="Font"
        depth=1
        next
    }

    /^[[:space:]]*\/XObject[[:space:]]*<</ {
        category="XObject"
        depth=1
        next
    }

    /^[[:space:]]*\/ColorSpace[[:space:]]*<</ {
        category="ColorSpace"
        depth=1
        next
    }

    /^[[:space:]]*\/ExtGState[[:space:]]*<</ {
        category="ExtGState"
        depth=1
        next
    }

    /^[[:space:]]*\/Pattern[[:space:]]*<</ {
        category="Pattern"
        depth=1
        next
    }

    /^[[:space:]]*\/Shading[[:space:]]*<</ {
        category="Shading"
        depth=1
        next
    }

    /^[[:space:]]*\/Properties[[:space:]]*<</ {
        category="Properties"
        depth=1
        next
    }

    # --------------------------------------------------------
    # Read entries from the resource dictionary
    #
    # Example:
    # /F1 27 0 R
    # --------------------------------------------------------

    category != "" {

        if ($1 ~ /^\// && $2 ~ /^[0-9]+$/ && $3 ~ /^[0-9]+$/ && $4 == "R") {

            name=$1
            object=$2
            prefix=prefix_of(name)
            number=number_of(name)

            print document "\t" category "\t" name "\t" prefix "\t" number "\t" object
        }

        opens=gsub(/<</, "<<")
        closes=gsub(/>>/, ">>")

        depth += opens
        depth -= closes

        if (depth <= 0) {
            category=""
            depth=0
        }
    }

    ' "$qdf"
}


echo
echo "=============================================="
echo "COS 721 Assignment 2 - Part 1 TEST"
echo "=============================================="
echo

document="${1:-$(head -n 1 "$OBS/all" | tr -d '\r[:space:]')}"

echo "Testing document: $document"

pdf="$(find_pdf "$document")"

if [[ -z "$pdf" ]]
then
    echo "ERROR: PDF not found."
    exit 1
fi

echo "PDF:"
echo "$pdf"
echo

qdf="$QDFDIR/${document}.qdf"

if ! qpdf \
    --qdf \
    --object-streams=disable \
    "$pdf" \
    "$qdf" \
    2>> "$ERRORS"
then
    echo "QPDF failed."
    cat "$ERRORS"
    exit 1
fi

echo "QDF created successfully."
echo

extract_resources "$document" "$qdf" >> "$RAW"

echo "=============================================="
echo "EXTRACTED RESOURCES"
echo "=============================================="
echo

column -t -s $'\t' "$RAW"

echo
echo "Number of extracted resource entries:"
tail -n +2 "$RAW" | wc -l
echo
