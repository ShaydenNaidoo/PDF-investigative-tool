#!/usr/bin/env bash

set -u

BASE="$HOME/COS 721/environment_set/environment"
OBS="$BASE/observations"
CAT="$BASE/pdfwork/cat"

DATASET="$HOME/COS 721/environment_set/master-gdc-gdcdatasets-2020445568-2020445568/lcwa_gov_pdf_data/data"

mkdir -p "$CAT"

TOTAL=$(grep -cve '^[[:space:]]*$' "$OBS/all")
COUNT=0

echo "Building readable PDF copies..."
echo "Documents: $TOTAL"
echo

while IFS= read -r DOC
do
    DOC=$(echo "$DOC" | tr -d '\r[:space:]')

    [ -z "$DOC" ] && continue

    COUNT=$((COUNT + 1))

    printf "[%4d/%4d] %s " "$COUNT" "$TOTAL" "$DOC"

    PDF=$(find "$DATASET" \
        -type f \
        -iname "${DOC}*.pdf" \
        -print \
        -quit)

    if [ -z "$PDF" ]
    then
        echo "NOT FOUND"
        continue
    fi

    if qpdf \
        --qdf \
        --object-streams=disable \
        "$PDF" \
        "$CAT/$DOC" \
        2>/dev/null
    then
        echo "OK"
    else
        echo "QPDF ERROR"
        rm -f "$CAT/$DOC"
    fi

done < "$OBS/all"

echo
echo "Finished."
echo "Files created:"
find "$CAT" -type f | wc -l

