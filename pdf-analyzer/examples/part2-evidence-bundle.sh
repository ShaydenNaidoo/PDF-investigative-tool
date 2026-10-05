#!/usr/bin/env bash
set -euo pipefail

: "${PDF_ANALYZER_HOME:?Run this script in PDF Analyzer}"
: "${PDF_OBSERVATIONS_DIR:?Missing observations path}"
: "${PDF_RUN_DIR:?Missing run output path}"

# Change only this value to investigate a different exemplar tool.
export PDF_INVESTIGATION_TOOL="pr01"

# A quoted heredoc passes Python source literally, without Bash expansion.
python3 - <<'PY'
from collections import defaultdict
import csv
import os
from pathlib import Path
import re
import subprocess
import sys

sys.path.insert(0, os.environ["PDF_ANALYZER_HOME"])
import lab

tool = os.environ["PDF_INVESTIGATION_TOOL"]
if not re.fullmatch(r"pr(?:0[1-9]|1[0-5])", tool):
    raise SystemExit("Choose a tool ID from pr01 through pr15")

observations = Path(os.environ["PDF_OBSERVATIONS_DIR"])
output = Path(os.environ["PDF_RUN_DIR"])
documents = lab.lines(observations / "tools" / tool)
if not documents:
    raise SystemExit(f"No exemplars found for {tool}")
index = lab.pdf_index()
resources, numbering_rows, failures = [], [], []

for position, document in enumerate(documents, 1):
    print(f"[{position}/{len(documents)}] {tool}: {document}", file=sys.stderr, flush=True)
    try:
        if document not in index:
            raise ValueError("Original PDF missing from dataset")
        rows, warning = lab.resource_rows(document, index[document])
        resources.extend(rows)
        # Summarize one PDF at a time: scope IDs are local to that PDF.
        numbering_rows.extend(lab.numbering(rows))
        if warning:
            print(f"{document}: {warning}", file=sys.stderr)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        failures.append({"document": document, "error": str(error)})
        print(f"{document}: {error}", file=sys.stderr)

# Compare names only within the same document and resource type.
# An object number in one PDF cannot be compared with that number in another PDF.
groups = defaultdict(list)
for row in resources:
    groups[(row["document"], row["resource_type"], row["resource_name"])].append(row)

reuse = []
for (document, kind, name), group in sorted(groups.items()):
    scopes = sorted({row["scope"] for row in group})
    if len(scopes) < 2:
        continue
    targets = sorted({row["reference"] for row in group})
    if "direct" in targets:
        relation = "direct value present; inspect owner definitions"
    else:
        relation = "same original object" if len(targets) == 1 else "different original objects"
    reuse.append({"document": document, "resource_type": kind, "resource_name": name,
                  "scope_count": len(scopes), "scopes": "; ".join(scopes),
                  "target_count": len(targets), "targets": "; ".join(targets),
                  "relation": relation})


def save_table(filename, headers, rows):
    with (output / filename).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


save_table("resources.tsv", ["document", "resource_type", "subtype", "resource_name", "prefix",
                           "number", "object", "reference", "scope", "owner"], resources)
save_table("numbering.tsv", ["document", "resource_type", "prefix", "scope", "start", "end",
                           "distinct_numbers", "missing_between", "suffix_equals_object", "entries"],
           numbering_rows)
save_table("reuse.tsv", ["document", "resource_type", "resource_name", "scope_count", "scopes",
                       "target_count", "targets", "relation"], reuse)
save_table("failures.tsv", ["document", "error"], failures)
print(f"Saved resources, numbering, reuse and failures tables for {tool}.", file=sys.stderr)
raise SystemExit(1 if failures else 0)
PY
