# Building investigation scripts in PDF Analyzer

This guide is for **your local PDF Analyzer app** and your **COS 721 Assignment 2**, especially Part 2's resource-numbering investigation. It explains how to generate a script, edit it, run it, produce tables, inspect the evidence, and build your own investigations.

The code blocks described as complete scripts can be pasted directly into the app's Bash editor. The accompanying files in [`examples/`](examples/) contain the same scripts.

## 1. Open the app and build your first investigation

1. In VS Code, open the Command Palette with **Ctrl+Shift+P**.
2. Choose **Tasks: Run Task → Start PDF Analyzer**. The task opens the app at <http://127.0.0.1:8766>. Keep it running while investigating.
3. Open **Script studio → Build a script**.
4. Set the builder controls as follows:

   | Control | Value for this first investigation |
   | --- | --- |
   | Investigation | **Numbering & gaps by local scope** |
   | Exemplar tool | **pr01** |
   | Document IDs | **Clear this field completely** |
   | Resource type | **Any resource** |
   | Exact prefix | **Leave blank** |

5. Click **Generate script**. Read the code that appears in the editor.
6. Set **Script name** to `part2-pr01-numbering`.
7. Click **Save script**, then **Run investigation**. Running an editor draft also saves it automatically.
8. Watch **Live output** for progress and errors. `[progress / stderr]` includes normal progress messages; it does not always indicate an error.
9. When the status is **COMPLETED**, click **View results**.
10. Search the result table, click a column heading to sort, use **Next / Previous** to page through rows, and click **Export CSV** to download all matching rows in the selected table.
11. Click a document ID in the results to open its inspector. Use **Resources** and **Numbering & reuse** to inspect individual examples and original object definitions.

The default Document IDs field contains `22ZOC`. Clearing it is essential when you want **all exemplars of a tool**. If a chosen document is not an exemplar of the selected tool, their intersection is empty and the run may successfully produce no matching rows.

### What the first script means

The generated script will be equivalent to:

```bash
#!/usr/bin/env bash
set -euo pipefail

python3 "$PDF_ANALYZER_HOME/lab.py" numbering --tool 'pr01'
```

| Piece | Meaning |
| --- | --- |
| `#!/usr/bin/env bash` | Identify the script as Bash. The app explicitly runs saved scripts with Bash. |
| `set -e` | Stop on many unhandled command failures. Errors inside conditions are handled separately. |
| `set -u` | Report accidental use of an unset variable. |
| `set -o pipefail` | Report failure from any command in a pipeline. |
| `python3` | Run the app's Python investigation helper. |
| `"$PDF_ANALYZER_HOME/lab.py"` | Locate that helper using the path supplied by the app. Quotes preserve spaces in `COS 721`. |
| `numbering` | Produce the numbering summary. |
| `--tool 'pr01'` | Investigate IDs listed in `observations/tools/pr01`. |

You do not need to reproduce the PDF parser to start investigating. Call the existing helper, then build additional comparisons around its output when needed.

## 2. Choose the scope and filters deliberately

### Investigation modes

| Builder label | Helper mode | Output |
| --- | --- | --- |
| Resource names & original references | `resources` | Resource names, numeric suffixes, subtypes, original object references and local scopes |
| Numbering & gaps by local scope | `numbering` | Minimum/maximum suffixes, distinct-number counts, gaps and matches to object numbers |
| Producer & creator metadata | `metadata` | Producer, creator, page count, PDF version and dates reported by `pdfinfo` |
| Existing toolmarks | `marks` | Membership in existing `observations/marks` sets |
| Blank Bash script | No helper call | A starting point for your own script |

Resource type and prefix controls are added to generated **resources** and **numbering** scripts. The builder does not add them to metadata or marks investigations.

### Scope rules

| Exemplar tool | Document IDs | What is investigated |
| --- | --- | --- |
| All documents | Blank | Every ID in `observations/all` |
| `pr01` | Blank | Every exemplar ID in `observations/tools/pr01` |
| All documents | `GGGXC` | Only `GGGXC` |
| All documents | `GGGXC,CUF7M,QZ74K` | Those three documents |
| `pr01` | One or more IDs | Only IDs that are also `pr01` exemplars |

Tool IDs are `pr01` through `pr15`. Document IDs are the five-character identifiers in `observations/all`. The helper accepts comma-separated IDs and normalizes their case. The helper's result order follows the observation set rather than the order typed into the field.

Choose **All documents** when investigating a document outside a particular tool's exemplar set. Unknown document IDs are reported as errors.

### Resource types and prefixes

Supported resource categories are case-sensitive:

```text
Font
XObject
ColorSpace
ExtGState
Pattern
Shading
Properties
```

`XObject` is a category that can contain **Image** and **Form** subtypes. Select `XObject`, then inspect `subtype` in the resource table to distinguish them. `Image` is not a valid category filter for this helper.

An exact prefix filter includes the leading slash and is case-sensitive. `/F`, `/TT`, `/Im`, `/Image` and `/img` are different values. Blank means no prefix filter. A prefix filter of `/F` does not mean any name beginning with the letter F: it selects rows whose extracted prefix is exactly `/F`.

Examples of helper calls you can put inside a Bash script:

```bash
# Font numbering for every exemplar of tool 12.
python3 "$PDF_ANALYZER_HOME/lab.py" numbering --tool pr12 --type Font
```

```bash
# Original /TT font references in one document.
python3 "$PDF_ANALYZER_HOME/lab.py" resources \
    --document QZ74K --type Font --prefix '/TT'
```

```bash
# Producer metadata for one exemplar set.
python3 "$PDF_ANALYZER_HOME/lab.py" metadata --tool pr01
```

```bash
# Existing observation marks for two documents.
python3 "$PDF_ANALYZER_HOME/lab.py" marks --document 'GGGXC,QZ74K'
```

These blocks demonstrate individual calls. **Do not concatenate several helper tables into stdout**: each prints its own header. Use the multiple-table pattern in section 6 instead.

## 3. Understand where scripts run and where they write

Every GUI investigation runs with this working directory:

```text
environment_set/environment/observations
```

That makes paths such as `tools/pr01`, `marks/`, `vectors/` and `all` meaningful. Use the provided variables for explicit paths:

| Variable | Meaning | Example use |
| --- | --- | --- |
| `PDF_ANALYZER_HOME` | App directory containing `lab.py` | `"$PDF_ANALYZER_HOME/lab.py"` |
| `PDF_OBSERVATIONS_DIR` | Observation directory | `"$PDF_OBSERVATIONS_DIR/tools/pr01"` |
| `PDF_DATASET_DIR` | Original PDF corpus directory | Search it for an ID's PDF |
| `PDF_RUN_DIR` | Current run's dedicated output directory | `"$PDF_RUN_DIR/numbering.tsv"` |

The app supplies these variables. Pasting an example into an unrelated terminal without supplying them is a different execution environment.

Always quote path variables. Your project path contains a space. Do not change `HOME` to locate the assignment.

Saved custom scripts live in:

```text
observations/gui-scripts/<script-name>.sh
```

Each run has its own directory:

```text
observations/gui-runs/<run-id>/
    script.sh           # Copy of the code executed
    stdout.log          # Standard output
    stderr.log          # Progress and errors
    run.json            # Run ID, timestamps, status, exit code and table list
    ...your .tsv files
```

The app executes a frozen copy of the script. Editing the saved script does not change an investigation already running. Do not rely on the saved script's own directory to locate the dataset; use the variables above.

Use letters, numbers, dashes and underscores for script names, up to 64 characters without the extension. Use descriptive names such as `part2-pr12-fonts`. Saving under an existing name replaces that saved script; past runs retain their own copies. **Generate script** replaces the editor's current draft, so save a draft you want to keep before generating another.

Runs execute with your local account's permissions. Put new investigation outputs in `PDF_RUN_DIR` so each run has separate evidence. The supplied `test_part1.sh` uses `part1-test-results`, whereas `part1_resources.sh` uses `part1-results`. `scan_resources.sh` is excluded from the app's script catalog.

## 4. Make the app display a results table

A TSV file is a table whose columns are separated by actual tab characters. It needs a header naming the columns.

### Option A: Print one TSV table to stdout

This is the simplest complete custom script:

```bash
#!/usr/bin/env bash
set -euo pipefail

printf 'Starting my investigation\n' >&2

printf 'document\tobservation\n'
printf '%s\t%s\n' 'GGGXC' 'A note to verify against the PDF'
```

`printf` turns `\t` into a tab and `\n` into a newline. Its format string is fixed; values are supplied as `%s` arguments. This avoids treating characters inside a value as formatting instructions.

The app recognizes stdout as TSV when its first nonblank line contains a tab. For stdout tables, use at least two columns. Ordinary one-item-per-line output becomes a generic **line / result** table instead.

Make the header the **very first stdout line**, without preceding blank lines. Print it **once**, then data rows with the same columns in the same order. Send progress and explanations to stderr with `>&2`; mixing messages such as `Starting...` into stdout can prevent TSV recognition or become misleading table rows.

### Option B: Write named TSV files to the current run directory

```bash
#!/usr/bin/env bash
set -euo pipefail

python3 "$PDF_ANALYZER_HOME/lab.py" resources --document GGGXC \
    > "$PDF_RUN_DIR/resources.tsv"

python3 "$PDF_ANALYZER_HOME/lab.py" numbering --document GGGXC \
    > "$PDF_RUN_DIR/numbering.tsv"

printf 'Saved two evidence tables.\n' >&2
```

After completion, both files appear in the **Investigation results** table selector. Select a table, filter it, then export CSV. The app scans top-level `.tsv` files in `PDF_RUN_DIR`; it does not automatically discover files in subdirectories or arbitrary `.csv`, `.json` or `.txt` files.

Avoid naming your own output `results.tsv` when you also print stdout: the app uses that name for its automatically captured stdout table. Names such as `resources.tsv`, `numbering.tsv` and `reuse.tsv` keep the outputs distinct.

For arbitrary text containing tabs, quotes or newlines, use Python's `csv.DictWriter(..., delimiter="\t")` to escape fields correctly, as in the evidence-bundle example. Simple Bash `printf` does not escape embedded tabs/newlines inside values.

## 5. Interpret the columns before drawing conclusions

### Original resource evidence

| Column | Meaning |
| --- | --- |
| `document` | Dataset ID |
| `resource_type` | Dictionary category, such as Font or XObject |
| `subtype` | Target object's subtype, when available; XObjects may be Image or Form |
| `resource_name` | Complete local name, such as `/TT4` |
| `prefix` | Name with its final run of decimal digits removed |
| `number` | That trailing numeric text; blank for names such as `/Helv` |
| `object` | Original target object number; blank for direct values |
| `reference` | Original object number and generation, such as `28 0 R`, or `direct` |
| `scope` | Identity of the local resource dictionary |
| `owner` | An object in which the resource dictionary was observed |

Only final digits are split from the name. For `/C2_0`, the helper reports prefix `/C2_` and number `0`; deciding whether that captures the tool's meaningful convention is part of your analysis. Leading zeros remain visible in the resource table, while numbering summaries compare suffixes numerically.

`scope` is **not a page number**. It can represent a page, a form or another resource context. Shared indirect resource dictionaries are deduplicated as one scope even when referenced by multiple owners; `owner` is not an exhaustive list of every page using a shared dictionary.

Resources are extracted from `/Resources` dictionaries, including indirect dictionaries and forms. A declared resource is not necessarily used in a content stream. The helper does not establish actual content-stream use or extract every possible resource-like entry elsewhere in the PDF, such as a separate AcroForm `/DR` dictionary.

An object number has meaning within its own PDF. Object 28 in one PDF is not the same resource as object 28 in another PDF. Compare complete references **within a document** when investigating name reuse. Direct values do not have an indirect object reference; inspect their owning definitions before deciding whether they identify the same resource.

### Numbering evidence

Each row groups resources by **document + resource type + prefix + local scope**.

| Column | Meaning |
| --- | --- |
| `start` | Lowest observed numeric suffix in that group |
| `end` | Highest observed numeric suffix |
| `distinct_numbers` | Number of different numeric suffix values |
| `missing_between` | Missing numbers between the observed minimum and maximum; large gaps may appear as ranges |
| `suffix_equals_object` | Number of resource entries whose numeric suffix matches their original target object number |
| `entries` | Total extracted entries in the group |

A blank `missing_between` means no gap **between the observed extremes**, not proof that all possible resources were created or used. One number also has no internal gap. A blank start/end means no numeric suffix was found, not that numbering starts at zero.

`suffix_equals_object` counts numeric, indirect-target matches. Static names and direct values do not match. Use the original resource table to inspect individual matches and exceptions; a match of object number alone says nothing about why the name was chosen.

For Part 2, check observed starts, increments, skipped values, reuse and targets across exemplars. The brief allows an incremental-numbering inference under its stated conditions: a consistent starting point, incremental numbering, no skipped values, and at least two increments. Three consecutive values in one sequence, or two separate two-value sequences, can provide those increments. The summary alone does not establish those conditions across a whole tool.

Use the document inspector to examine contradictions. Record concrete document IDs, scopes and original references in your notebook. Your report should explain whether observed numbering conventions differentiate tools, with examples and counterexamples.

**Use original-PDF investigations for object-number claims.** The older resource extraction under `part1-results` is based on QDF conversion, which may renumber objects.

## 6. Complete scripts you can copy and customize

For any example below:

1. Open **Script studio → Build a script**.
2. Paste the complete Bash script into the editor, without Markdown fences.
3. Change the values called out in the comments.
4. Give it a descriptive **Script name**.
5. Save, run, inspect the run status, then open its results tables.

Once you edit the code manually, the **code in the editor** determines the investigation. Changing a builder dropdown does not change the existing code until you click **Generate script** again, which replaces the draft.

### A. Numbering for one exemplar tool

Change `tool="pr01"` to the tool you want. This creates one stdout table covering all supported resource types for that tool. Add `--type Font` or `--prefix '/F'` to the helper call only when you want those restrictions.

Source file: [`part2-numbering-tool.sh`](examples/part2-numbering-tool.sh).

```bash
#!/usr/bin/env bash
set -euo pipefail

: "${PDF_ANALYZER_HOME:?Run this script in PDF Analyzer}"

# Change this to any exemplar tool from pr01 to pr15.
tool="pr01"

# Omit --document to include every exemplar of the selected tool.
# Omit --type and --prefix to include every supported resource category.
python3 "$PDF_ANALYZER_HOME/lab.py" numbering --tool "$tool"
```

### B. Resource evidence for selected documents

Change the comma-separated `documents` value. This keeps names, subtypes, scopes and original references so you can compare numbering and inspect reuse. It selects documents directly without an exemplar-tool restriction.

Source file: [`part2-resources-documents.sh`](examples/part2-resources-documents.sh).

```bash
#!/usr/bin/env bash
set -euo pipefail

: "${PDF_ANALYZER_HOME:?Run this script in PDF Analyzer}"

# Use comma-separated IDs from observations/all.
documents="GGGXC,CUF7M,QZ74K"

# Keep original object references, local scopes and XObject subtypes.
python3 "$PDF_ANALYZER_HOME/lab.py" resources --document "$documents"
```

### C. A Part 2 evidence bundle: resources, numbering, reuse and failures

Change `PDF_INVESTIGATION_TOOL="pr01"`. This reads each original exemplar PDF once and creates four separate tables. The reuse table groups by document, resource type and complete resource name, then distinguishes identical versus different indirect targets across scopes. It flags direct values for manual inspection. `failures.tsv` identifies documents that could not be read; a run with such failures exits with status 1, although successfully collected evidence is still saved. An empty reuse table means no cross-scope name reuse was found in the extracted resources.

Source file: [`part2-evidence-bundle.sh`](examples/part2-evidence-bundle.sh).

```bash
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
```

### D. Inspect a specific original object with qpdf

Change `document` and `object_reference` after selecting an original resource row. `28,0` means object 28, generation 0. This produces a table with the original definition in one cell and preserves its unflattened text in the run directory. qpdf exit code 3 means warnings; this script keeps the evidence and labels the warning. Other nonzero exit codes stop the investigation. The GUI inspector also lets you read an indirect target by clicking its reference, without writing a script.

Source file: [`inspect-original-object.sh`](examples/inspect-original-object.sh).

```bash
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
```

### E. Batch numbering investigations for all 15 tools

This creates `pr01-numbering.tsv` through `pr15-numbering.tsv` in one run. Start with example A to check your method before batching. The run stops on an unhandled tool investigation failure; any tables already written remain available, so check the run status before treating the batch as complete. Choose the tool table using the results selector. There is no estimated runtime guarantee; the runner stops a run after 30 minutes.

Source file: [`all-tools-numbering.sh`](examples/all-tools-numbering.sh).

```bash
#!/usr/bin/env bash
set -euo pipefail

: "${PDF_ANALYZER_HOME:?Run this script in PDF Analyzer}"
: "${PDF_RUN_DIR:?Missing run output path}"

# One table per tool; overlapping exemplar IDs remain in their respective sets.
for ((number = 1; number <= 15; number++)); do
    printf -v tool 'pr%02d' "$number"
    printf 'Investigating %s\n' "$tool" >&2
    python3 "$PDF_ANALYZER_HOME/lab.py" numbering --tool "$tool" \
        > "$PDF_RUN_DIR/${tool}-numbering.tsv"
done
```

## 7. Build a different investigation yourself

Begin with one testable question, then decide what evidence would let you answer it.

| Question | Data to collect | Useful row structure |
| --- | --- | --- |
| Do fonts use consecutive suffixes in a scope? | Original resource names and numbering groups | document, type, prefix, scope, observed sequence, gaps |
| Does a name recur for the same target? | Name, complete reference and scope | document, type, name, scopes, targets |
| Do images and forms use different naming patterns? | XObject names and subtypes | document, subtype, name, prefix, number |
| Does a numeric suffix equal its original object number? | Numeric suffix and original target | document, name, number, reference, comparison |
| Which examples contradict a proposed convention? | Defined expectation and observed resources | document, scope, expected observation, actual observation |

Write the scope at the top of your script: tool ID, document IDs, or selected resource type. Use variable names that describe your investigation.

A practical development cycle is:

1. Run on one document whose resources you can inspect manually.
2. Compare the rows with **Evidence explorer → document inspector** and the original object definitions.
3. Check an example with multiple resources, multiple local scopes, or a known anomaly.
4. Confirm the script treats absent suffixes, direct values, empty output and warnings sensibly.
5. Expand to one exemplar tool, then additional tools if the test applies to them.
6. Save the evidence table and record the reasoning and limitations in **Field notebook**.

### Bash operations you will use

```bash
# A variable assignment has no spaces around =.
tool="pr01"

# Use the variable inside quotes.
printf 'Investigating %s\n' "$tool" >&2

# > creates/replaces a file. >> appends. Print a header once when appending rows.
printf 'document\tobservation\n' > "$PDF_RUN_DIR/my-evidence.tsv"
printf '%s\t%s\n' 'GGGXC' 'An observation to verify' >> "$PDF_RUN_DIR/my-evidence.tsv"

# >&2 sends progress to stderr; keep table data separate.
printf 'Progress message\n' >&2
```

For a multiple-line command, `\` must be the last character on the line. Do not place a comment or trailing spaces after it. For a Python heredoc such as `<<'PY'`, its closing `PY` must appear alone at the start of its line. The quotes in `<<'PY'` prevent Bash from substituting characters inside the Python code.

To read a document set without breaking IDs or interpreting backslashes:

```bash
while IFS= read -r document || [[ -n "$document" ]]; do
    document="${document%$'\r'}"
    [[ -z "$document" ]] && continue
    printf 'Selected document: %s\n' "$document" >&2
    # Put your per-document investigation here.
done < "$PDF_OBSERVATIONS_DIR/tools/pr01"
```

### When to use Bash and when to use Python inside it

Use Bash for selecting paths, invoking tools, loops and straightforward output. Use Python for structured PDF data, grouping many records, sorting numeric suffixes, comparing scopes and references, and writing quoted table cells. A Bash script containing a Python heredoc is still a script you can save and run in the app.

The bundle demonstrates the app helper functions you can import:

| Function | Result |
| --- | --- |
| `lab.lines(path)` | Nonblank, stripped lines from a file; empty list if absent |
| `lab.pdf_index()` | Map from document ID to original PDF path in the app's dataset |
| `lab.resource_rows(document, path)` | `(resource_rows, warning_text)` for an original PDF |
| `lab.numbering(resource_rows)` | Type/prefix/scope numbering summaries; pass rows from **one PDF per call** |
| `lab.metadata(document, path)` | Dictionary of `pdfinfo` values |

Import using `sys.path.insert(0, os.environ["PDF_ANALYZER_HOME"])` followed by `import lab`. These helpers are tied to the dataset configured in this app; changing an environment variable in your own script does not retarget the helper's internal dataset configuration.

When importing `lab.numbering`, call it separately for each PDF, as in example C. Scope strings such as `9 0 R` recur in unrelated PDFs; passing a corpus-wide list to that function would merge their scopes.

Keep scope in your grouping keys. Grouping every `/F1` in the corpus together loses the distinction between different PDFs and local dictionaries. For numbering, sort suffixes **numerically**: text sorting puts `10` before `2`. Keep the original names as well if leading zeros or complex naming conventions matter.

## 8. Tools available for custom investigations

The GUI runs your Bash script with the installed command-line tools. You still operate through the app; these calls belong in the editor.

| Tool/call | Use | Output considerations |
| --- | --- | --- |
| `python3 "$PDF_ANALYZER_HOME/lab.py" ...` | Structured resource, numbering, metadata or mark evidence | Emits a TSV table; progress goes to stderr |
| `qpdf --show-object=28,0 "$pdf"` | Original indirect object definition | Text/dictionary output; wrap it in a TSV row or inspect it in the GUI |
| `qpdf --show-pages "$pdf"` | Page-object and content-stream references | Text output, not an automatic structured PDF-resource table |
| `pdfinfo "$pdf"` | Producer/creator metadata, page count and related properties | Text output; helper metadata mode already structures selected fields |
| `pdftotext "$pdf" "$PDF_RUN_DIR/extracted-text.txt"` | Extract rendered document text | This is document text, not a resource-dictionary investigation |
| `awk`, `sed`, `sort`, `uniq` | Process known text/table formats | Preserve the header and avoid mixing separate tables |
| `find "$PDF_DATASET_DIR" ...` | Locate a PDF whose filename begins with a document ID | Quote the path and filename pattern; see example D |
| `./section tools/pr01 tools/pr02` | Intersect two existing observation sets | One member per line; shown as a generic result table |
| `./minus classes/pr01 tools/pr01` | Find class members that are not exemplars | Uses existing classification outputs, which must be up to date |

Do not infer resource categories or usage by searching every occurrence of `/F1` in PDF bytes. A string can occur in unrelated contexts, and streams may be compressed. The app's helper follows structured resource dictionaries and resolves indirect references.

For numbering/object comparisons, examine the **original PDF** with qpdf JSON or `--show-object`. Rewriting a PDF into QDF can change object numbers.

The vector, bag, feature-vector and class scripts are available in **Script library**, but they rebuild their respective observation files and depend on earlier stages. They are not prerequisites for the original-PDF numbering helper. Custom scripts have no separate GUI arguments box; change the variables or helper arguments inside your custom code. Argument boxes in the library are for the supplied helpers that explicitly accept arguments.

## 9. Troubleshooting and checking your evidence

| What you see | Likely cause | What to do |
| --- | --- | --- |
| Lab disconnected / cannot run | Backend is not running, or page points at the wrong server | Run **Start PDF Analyzer**, open its URL, and reload |
| Bash syntax error while saving | Broken quoting, missing `fi`/`done`, copied Markdown fences, malformed heredoc | Fix the indicated syntax; paste only code into the editor |
| Script saves, but Python fails at runtime | Bash syntax checks do not validate embedded Python or the investigation's logic | Read the Python traceback in Live output |
| Unknown document ID | ID is not in `observations/all`, or full filenames were entered instead | Enter a five-character ID; comma-separate multiple IDs |
| Invalid tool | Tool ID is not `pr01` through `pr15` | Use the exact tool identifier |
| COMPLETED with no matching rows | Tool/document intersection is empty, filters exclude all resources, or none were found | Check Document IDs, tool, exact case of type/prefix, and the original PDF |
| Start/end cells blank | Names in that group have no numeric suffix | Inspect complete names; do not read blank as zero |
| Only a generic line/result table | stdout was plain text or its first nonblank line did not contain tabs | Print one TSV header first, or write a named `.tsv` file |
| Extra headers inside the table | Several helper calls were concatenated into stdout | Redirect each helper to a different `.tsv` file |
| A progress sentence appears as data | Progress was printed to stdout | Add `>&2` to progress messages |
| Named table does not appear | File was outside `PDF_RUN_DIR`, in a subdirectory, had another extension, or the run is unfinished | Write a top-level `.tsv` file in the current run directory and wait for completion |
| An output file was replaced | Reused a filename inside one run, or collided with automatic `results.tsv` | Use distinct descriptive filenames |
| Original object differs from the old table | Old extraction used QDF numbering | Verify with original resources and the original object inspector |
| FAILED with some populated tables | An investigation failed after collecting partial evidence | Inspect stderr and any `failures.tsv`; do not treat that run as complete |
| qpdf warning in stderr | qpdf recovered or reported a PDF issue | Read the warning; the helper accepts qpdf warning exit code 3 and preserves readable evidence |
| Another investigation is running | The runner serializes investigations | Wait for it or click **Stop**, then start the next run |
| CANCELLED or INTERRUPTED | Run was stopped or the server ended | Treat outputs as partial; rerun if complete evidence is required |
| Timeout | Run exceeded the 30-minute runner limit or a per-document helper timeout | Narrow the scope and run smaller investigations |

The helper reads qpdf JSON from an original PDF with a per-document timeout of 90 seconds; metadata uses a 30-second timeout. Table files become available when the runner finishes collecting the results. The console displays the tail of very large logs, whereas the complete stdout/stderr files are preserved in the run directory.

A successful exit means the script completed without reporting a handled failure. It does not prove a naming convention. A gap does not prove editing. Resource declaration does not prove actual use. Record these distinctions alongside your observations.

## 10. A repeatable Part 2 workflow

1. Choose one exemplar tool and run **example A** or the GUI numbering template without a Document IDs restriction.
2. Run **example C** for the same tool to collect original names, numbering groups and name reuse together.
3. Inspect selected documents and exceptions using the document inspector; use **example D** when you want a saved object-definition table.
4. Record observed starts, increments, gaps, reuse, target identities and supporting document IDs in Field notebook.
5. Repeat for other exemplar tools. Use **example E** to batch numbering after checking the method on a smaller set.
6. Investigate the assignment's examples separately using **example B**, rather than unintentionally restricting them to a tool's exemplar set.
7. Export the tables you need. Build a concise comparison of your observations and explain which numbering patterns differentiate tools, which are shared, and which counterexamples limit your inference.

Keep the report's discussion grounded in your inspected examples. The app gathers and organizes evidence; you decide whether it supports the conditions and conclusions in the [assignment brief](../assign2.pdf).
