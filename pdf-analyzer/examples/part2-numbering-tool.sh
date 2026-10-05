#!/usr/bin/env bash
set -euo pipefail

: "${PDF_ANALYZER_HOME:?Run this script in PDF Analyzer}"

# Change this to any exemplar tool from pr01 to pr15.
tool="pr01"

# Omit --document to include every exemplar of the selected tool.
# Omit --type and --prefix to include every supported resource category.
python3 "$PDF_ANALYZER_HOME/lab.py" numbering --tool "$tool"
