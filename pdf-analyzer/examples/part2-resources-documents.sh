#!/usr/bin/env bash
set -euo pipefail

: "${PDF_ANALYZER_HOME:?Run this script in PDF Analyzer}"

# Use comma-separated IDs from observations/all.
documents="GGGXC,CUF7M,QZ74K"

# Keep original object references, local scopes and XObject subtypes.
python3 "$PDF_ANALYZER_HOME/lab.py" resources --document "$documents"
