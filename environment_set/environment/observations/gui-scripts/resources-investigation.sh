#!/usr/bin/env bash
set -euo pipefail

# Working directory: observations
# Read original PDFs; keep source object references.
# Structured output becomes a results table automatically.
python3 "$PDF_ANALYZER_HOME/lab.py" resources --document '22ZOC'
