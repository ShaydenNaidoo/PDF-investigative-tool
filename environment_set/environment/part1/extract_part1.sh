#!/usr/bin/env bash

set -u

# ============================================================
# COS 721 Assignment 2 - Part 1
# PDF Resource Naming Investigation
# Bash-only workflow
# ============================================================


ENVIRONMENT="$HOME/COS 721/environment_set/environment"

TOOLS_DIR="$ENVIRONMENT/observations/tools"

DATASET="$HOME/COS 721/environment_set/master-gdc-gdcdatasets-2020445568-2020445568/lcwa_gov_pdf_data/data"

WORK="$ENVIRONMENT/part1"

QDF_DIR="$WORK/qdf"

RESULTS="$WORK/results"


mkdir -p "$QDF_DIR"
mkdir -p "$RESULTS"


RAW="$RESULTS/part1_resources.csv"
MISSING="$RESULTS/missing_documents.txt"
ERRORS="$RESULTS/errors.txt"


echo 'tool,document,resource_type,resource_name,prefix,number,object_number,pdf' > "$RAW"

: > "$MISSING"
: > "$ERRORS"


# ------------------------------------------------------------
# Check required commands
# ------------------------------------------------------------

for cmd in qpdf awk sed grep find
do
    if ! command -v "$cmd" >/dev/null 2>&1
    then
        echo "ERROR: $cmd is not installed."
        exit 1
    fi
done


if [[ ! -d "$TOOLS_DIR" ]]
then
    echo "ERROR: Cannot find tools directory:"
    echo "$TOOLS_DIR"
    exit 1
fi


if [[ ! -d "$DATASET" ]]
then
    echo "ERROR: Cannot find dataset:"
    echo "$DATASET"
    exit 1
fi


# ------------------------------------------------------------
# Get resource prefix
#
# /F12     -> /F
# /TT3     -> /TT
# /Image9  -> /Image
# ------------------------------------------------------------

get_prefix()
{
    local name="$1"

    echo "$name" | sed -E 's/[0-9]+$//'
}


# ------------------------------------------------------------
# Get numeric suffix
#
# /F12 -> 12
# /TT3 -> 3
# ------------------------------------------------------------

get_number()
{
    local name="$1"

    if [[ "$name" =~ ([0-9]+)$ ]]
    then
        echo "${BASH_REMATCH[1]}"
    else
        echo ""
    fi
}


# ------------------------------------------------------------
# Find PDF using 5-character ID
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
# Determine whether XObject is Image or Form
# ------------------------------------------------------------

xobject_type()
{
    local qdf="$1"
    local object_number="$2"

    if [[ -z "$object_number" ]]
    then
        echo "XObject"
        return
    fi

    local result

    result="$(
        awk -v obj="$object_number" '

        $1 == obj && $2 == "0" && $3 == "obj" {
            inside=1
        }

        inside && /\/Subtype[[:space:]]+\/Image/ {
            print "Image"
            exit
        }

        inside && /\/Subtype[[:space:]]+\/Form/ {
            print "Form"
            exit
        }

        inside && /^endobj/ {
            exit
        }

        ' "$qdf"
    )"

    if [[ -z "$result" ]]
    then
        echo "XObject"
    else
        echo "$result"
    fi
}


# ------------------------------------------------------------
# Extract resource dictionary category
# ------------------------------------------------------------

extract_category()
{
    local qdf="$1"
    local category="$2"
    local readable_type="$3"
    local tool="$4"
    local document="$5"
    local pdf="$6"

    awk -v category="$category" '

    BEGIN {
        inside=0
        depth=0
    }

    $0 ~ "/" category "[[:space:]]*<<" {
        inside=1
        depth=1
        next
    }

    inside {

        opens = gsub(/<</, "<<")
        closes = gsub(/>>/, ">>")

        depth += opens
        depth -= closes

        if (
            $1 ~ /^\// &&
            $2 ~ /^[0-9]+$/ &&
            $3 ~ /^[0-9]+$/ &&
            $4 == "R"
        ) {
            print $1 "|" $2
        }

        if (depth <= 0) {
            inside=0
            depth=0
        }
    }

    ' "$qdf" |
    while IFS='|' read -r resource object_number
    do
        [[ -z "$resource" ]] && continue

        prefix="$(get_prefix "$resource")"
        number="$(get_number "$resource")"

        actual_type="$readable_type"

        if [[ "$readable_type" == "XObject" ]]
        then
            actual_type="$(xobject_type "$qdf" "$object_number")"
        fi

        printf '"%s","%s","%s","%s","%s","%s","%s","%s"\n' \
            "$tool" \
            "$document" \
            "$actual_type" \
            "$resource" \
            "$prefix" \
            "$number" \
            "$object_number" \
            "$pdf" \
            >> "$RAW"

    done
}


# ------------------------------------------------------------
# Process one PDF
# ------------------------------------------------------------

process_pdf()
{
    local tool="$1"
    local document="$2"
    local pdf="$3"

    local qdf="$QDF_DIR/${tool}_${document}.qdf.pdf"

    echo "    Converting with qpdf..."

    if ! qpdf \
        --qdf \
        --object-streams=disable \
        "$pdf" \
        "$qdf" \
        2>> "$ERRORS"
    then
        echo "    [!] qpdf failed"
        echo "$tool $document $pdf" >> "$ERRORS"
        return
    fi

    extract_category "$qdf" "Font"       "Font"       "$tool" "$document" "$pdf"
    extract_category "$qdf" "XObject"    "XObject"    "$tool" "$document" "$pdf"
    extract_category "$qdf" "ColorSpace" "ColorSpace" "$tool" "$document" "$pdf"
    extract_category "$qdf" "ExtGState"  "ExtGState"  "$tool" "$document" "$pdf"
    extract_category "$qdf" "Pattern"    "Pattern"    "$tool" "$document" "$pdf"
    extract_category "$qdf" "Shading"    "Shading"    "$tool" "$document" "$pdf"
    extract_category "$qdf" "Properties" "Properties" "$tool" "$document" "$pdf"
}


# ============================================================
# MAIN
# ============================================================

echo
echo "==============================================="
echo " COS 721 Assignment 2 - Part 1"
echo "==============================================="
echo

echo "Tools directory:"
echo "$TOOLS_DIR"
echo

echo "Dataset:"
echo "$DATASET"
echo


for tool_file in "$TOOLS_DIR"/pr*
do
    [[ -f "$tool_file" ]] || continue

    tool="$(basename "$tool_file")"

    echo
    echo "==============================================="
    echo "TOOL: $tool"
    echo "==============================================="

    count=0

    while IFS= read -r document
    do
        document="$(echo "$document" | tr -d '\r[:space:]')"

        [[ -z "$document" ]] && continue

        ((count++))

        echo
        echo "[$count] $document"

        pdf="$(find_pdf "$document")"

        if [[ -z "$pdf" ]]
        then
            echo "    [!] PDF NOT FOUND"
            echo "$tool $document" >> "$MISSING"
            continue
        fi

        echo "    $pdf"

        process_pdf \
            "$tool" \
            "$document" \
            "$pdf"

    done < "$tool_file"

done


echo
echo "==============================================="
echo " Extraction complete"
echo "==============================================="
echo

echo "Raw data:"
echo "$RAW"

echo
echo "Missing documents:"
echo "$MISSING"

echo
echo "Errors:"
echo "$ERRORS"
