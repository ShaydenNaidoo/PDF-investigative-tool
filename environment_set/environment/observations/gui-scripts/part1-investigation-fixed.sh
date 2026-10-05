#!/usr/bin/env bash
set -euo pipefail
trap 'status=$?; printf "ERROR: line %s: %s (exit %s)\n" "$LINENO" "$BASH_COMMAND" "$status" >&2; exit "$status"' ERR
# ============================================================
# COS 721 Assignment 2 - Part 1
# Resource-name convention investigation
# Bash + qpdf + awk only
# ============================================================

OBS="${PDF_OBSERVATIONS_DIR:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)}"

DATASET="${PDF_DATASET_DIR:-$(cd -- "$OBS/../../master-gdc-gdcdatasets-2020445568-2020445568/lcwa_gov_pdf_data/data" && pwd)}"

RESULTS="${PDF_RUN_DIR:?Run this inside PDF Analyzer}"
QDFDIR="$RESULTS/qdf"
RMARKS="$RESULTS/resource-marks"

RAW="$RESULTS/all-resources.tsv"
SUMMARY="$RESULTS/prefix-summary.tsv"
MISSING="$RESULTS/missing-pdfs.txt"
ERRORS="$RESULTS/qpdf-errors.txt"

for required in qpdf awk sed grep find sort uniq column; do
    command -v "$required" >/dev/null 2>&1 || { echo "ERROR: $required is required."; exit 1; }
done
[[ -d "$DATASET" && -f "$OBS/all" ]] || { echo "ERROR: Dataset or observations/all is missing."; exit 1; }

mkdir -p "$RESULTS"
mkdir -p "$QDFDIR"
mkdir -p "$RMARKS"

rm -f "$RMARKS"/*

: > "$MISSING"
: > "$ERRORS"

printf "document\tresource_type\tresource_name\tprefix\tnumber\tobject\n" > "$RAW"


# ------------------------------------------------------------
# Requirements
# ------------------------------------------------------------

for command in qpdf awk sed grep find sort uniq column
do
    if ! command -v "$command" >/dev/null 2>&1
    then
        echo "ERROR: $command is required."
        exit 1
    fi
done


if [[ ! -d "$DATASET" ]]
then
    echo "ERROR: Dataset directory not found:"
    echo "$DATASET"
    exit 1
fi


if [[ ! -f "$OBS/all" ]]
then
    echo "ERROR: observations/all not found."
    exit 1
fi


# ------------------------------------------------------------
# Find PDF by five-character document ID
# ------------------------------------------------------------

find_pdf()
{
    local id="$1"

    find "$DATASET" \
        -type f \
        -iname "${id}*.pdf" \
        -print \
        -quit
}


# ------------------------------------------------------------
# Convert prefix to safe filename text
#
# /F      -> F
# /TT     -> TT
# /Image  -> Image
# ------------------------------------------------------------

safe_prefix()
{
    echo "$1" |
        sed 's#^/##' |
        sed 's/[^A-Za-z0-9._-]/_/g'
}


# ------------------------------------------------------------
# Add document ID to resource-mark file
# ------------------------------------------------------------

add_mark()
{
    local document="$1"
    local type="$2"
    local prefix="$3"

    local safe_type
    local safe_pre

    safe_type="$(
        echo "$type" |
        tr '[:upper:]' '[:lower:]' |
        sed 's/[^a-z0-9]/_/g'
    )"

    safe_pre="$(safe_prefix "$prefix")"

    echo "$document" >> "$RMARKS/res-${safe_type}-${safe_pre}"
}


# ------------------------------------------------------------
# Extract resource mappings from QDF
#
# Handles direct resource dictionaries such as:
#
# /Font <<
#   /F1 20 0 R
#   /F2 21 0 R
# >>
#
# ------------------------------------------------------------

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


# ============================================================
# MAIN EXTRACTION
# ============================================================

TOTAL="$(awk 'NF { n++ } END { print n+0 }' "$OBS/all")"
COUNT=0

echo
echo "=============================================="
echo "COS 721 Assignment 2 - Part 1"
echo "Resource-name extraction"
echo "=============================================="
echo
echo "Documents expected: $TOTAL"
echo


while IFS= read -r document
do
    document="$(echo "$document" | tr -d '\r[:space:]')"

    [[ -z "$document" ]] && continue

    COUNT=$((COUNT + 1))

    printf "[%4d/%4d] %s " \
        "$COUNT" \
        "$TOTAL" \
        "$document"

    pdf="$(find_pdf "$document")"

    if [[ -z "$pdf" ]]
    then
        echo "MISSING"
        echo "$document" >> "$MISSING"
        continue
    fi

    qdf="$QDFDIR/${document}.qdf"

    # qpdf exits 3 when it produced output successfully with warnings.
    qpdf_status=0
    qpdf --qdf --object-streams=disable "$pdf" "$qdf" 2>> "$ERRORS" || qpdf_status=$?
    if [[ "$qpdf_status" -ne 0 && "$qpdf_status" -ne 3 ]] || [[ ! -s "$qdf" ]]; then
        echo "QPDF ERROR (exit $qpdf_status; see qpdf-errors.txt)"
        rm -f "$qdf"
        continue
    fi
    if [[ "$qpdf_status" -eq 3 ]]; then
        printf "QPDF WARNING (see qpdf-errors.txt) "
    fi

    temp="$RESULTS/.resources-${document}"

    extract_resources \
        "$document" \
        "$qdf" \
        > "$temp"

    if [[ -s "$temp" ]]
    then
        cat "$temp" >> "$RAW"

        while IFS=$'\t' read -r \
            doc \
            type \
            resource \
            prefix \
            number \
            object
        do
            add_mark "$doc" "$type" "$prefix"

        done < "$temp"

        lines="$(wc -l < "$temp")"

        echo "OK ($lines resources)"
    else
        echo "OK (no named resources found)"
    fi

    rm -f "$temp"
    rm -f "$qdf"

done < "$OBS/all"


# ------------------------------------------------------------
# Deduplicate resource mark files
# ------------------------------------------------------------

for mark in "$RMARKS"/*
do
    [[ -f "$mark" ]] || continue
    sort -u "$mark" -o "$mark"
done


# ============================================================
# BUILD PREFIX SUMMARY
# ============================================================

printf "tool\tresource_type\tprefix\tdocuments_with_prefix\texemplars\tpercentage\n" > "$SUMMARY"


for toolfile in "$OBS"/tools/pr*
do
    [[ -f "$toolfile" ]] || continue

    tool="$(basename "$toolfile")"

    exemplars="$(awk 'NF { n++ } END { print n+0 }' "$toolfile")"
    [[ "$exemplars" -eq 0 ]] && continue

    for mark in "$RMARKS"/*
    do
        [[ -f "$mark" ]] || continue

        basename_mark="$(basename "$mark")"

        rest="${basename_mark#res-}"

        type="${rest%%-*}"
        prefix="${rest#*-}"

        # A zero-overlap set is valid evidence. awk returns success even for zero.
        count="$(
            awk 'NR == FNR { if (NF) members[$0]=1; next }
                 ($0 in members) && !seen[$0]++ { n++ }
                 END { print n+0 }' "$toolfile" "$mark"
        )"

        if [[ "$count" -gt 0 ]]
        then
            percentage="$(
                awk -v c="$count" -v n="$exemplars" \
                    'BEGIN { printf "%.1f", (c/n)*100 }'
            )"

            printf "%s\t%s\t/%s\t%s\t%s\t%s%%\n" \
                "$tool" \
                "$type" \
                "$prefix" \
                "$count" \
                "$exemplars" \
                "$percentage" \
                >> "$SUMMARY"
        fi
    done
done


# Keep header, sort body
{
    head -n 1 "$SUMMARY"
    tail -n +2 "$SUMMARY" | sort -k1,1 -k2,2 -k3,3
} > "$SUMMARY.tmp"

mv "$SUMMARY.tmp" "$SUMMARY"


echo
echo "=============================================="
echo "PART 1 COMPLETE"
echo "=============================================="
echo

echo "Raw resource observations:"
echo "  $RAW"

echo
echo "Resource mark sets:"
echo "  $RMARKS"

echo
echo "Tool/prefix summary:"
echo "  $SUMMARY"

echo
echo "Missing PDFs:"
echo "  $MISSING"

echo
echo "qpdf warnings/errors:"
echo "  $ERRORS"
