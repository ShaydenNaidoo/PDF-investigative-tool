# PDF Analyzer · Vice Lab

A local COS 721 PDF investigation app with a Vice City inspired synthwave design: neon lights, an animated sunset, palm silhouettes, transitions, click ripples and live run effects. Motion respects your operating system's reduced-motion preference. Assets are local; no internet connection or third-party Python packages are needed.

## Open the GUI

In VS Code, open the Command Palette (`Ctrl+Shift+P`), choose **Tasks: Run Task**, then **Start PDF Analyzer**. The task starts the backend and opens your browser at <http://127.0.0.1:8766>. Keep the task running while using the app.

The backend can also be launched with `python3 pdf-analyzer/server.py --open`. Change the port with `--port` if 8766 is occupied. Required tools are `bash`, `qpdf` with JSON v2 support, `pdfinfo`, `awk`, `sed`, `grep`, `find`, `sort`, `uniq`, and `column`. Your environment already provides these.

## Investigate without terminal commands

- **Dashboard:** real dataset counts, resource-prefix frequencies, tool availability, and assignment examples to inspect.
- **Evidence explorer:** searchable documents and resource mappings, tool/type filters, sortable columns, pagination, and CSV exports of all matching rows.
- **Document inspector:** open the original PDF, inspect its producer/creator metadata, resource subtypes, local resource scopes, original object definitions, numbering gaps, name reuse, existing marks, and document notes.
- **Tool comparison:** prefixes by resource type for all 15 exemplar tools, with distinct-document counts and a configurable sparse-evidence threshold. Export the matrix to CSV.
- **Script studio:** run observation scripts, generate investigations from controls, edit/save Bash scripts, inspect live output and errors, stop runs, reopen history, filter result tables, and export CSV.
- **Field notebook:** save reasoning and document notes and export them together as Markdown.

## Build your own investigation scripts

Read the [Script Builder README](README_SCRIPT_BUILDER.md) for the full GUI walkthrough, scope/filter rules, Bash and Python examples, result-column definitions, TSV output format, original-object inspection, and troubleshooting. Copyable scripts are in [`examples/`](examples/).

## First investigation

1. Open **Script studio → Build a script**.
2. Choose **Resource names & original references** or **Numbering & gaps by local scope**.
3. Enter a document ID, for example `22ZOC` or `GGGXC`. Enter several IDs separated by commas. Clear the IDs to investigate all documents, or select an exemplar tool to limit the scope.
4. Optionally choose a resource type and exact prefix.
5. Click **Generate script**, review/edit it, then **Run investigation**.
6. Scroll to **Investigation results**, filter the evidence, and click **Export CSV**. Click any document ID to inspect the PDF.

The script library includes `part1_resources.sh`, `test_part1.sh`, the vector/bag/feature/class builders, and set operations. One-document helpers accept an ID, one-tool helpers accept `pr01` through `pr15`, and set operations accept paths such as `tools/pr01 tools/pr02`. Build the four classification stages in order: vectors, bags, feature vectors, classes. They use the existing marks; resource marks are not automatically added to that classification pipeline.

`scan_resources.sh` is excluded and has not been changed.

## Scripts and result files

Scripts run inside `environment_set/environment/observations` with the normal local account's permissions. Saved custom scripts are in `observations/gui-scripts`. Each run preserves a copy of its script, stdout/stderr, timestamps, status, exit code, and tables under `observations/gui-runs/<run-id>`. Runs are serialized so assignment scripts cannot concurrently overwrite shared outputs. A run has a 30-minute limit; stopping a run terminates its process group.

Custom scripts can print TSV with a header to stdout, or write `.tsv` files to `$PDF_RUN_DIR`. Plain stdout is shown as a line/result table. These environment variables are available:

| Variable | Path |
| --- | --- |
| `PDF_OBSERVATIONS_DIR` | observations directory |
| `PDF_DATASET_DIR` | original PDF dataset |
| `PDF_ANALYZER_HOME` | app directory containing `lab.py` |
| `PDF_RUN_DIR` | current run's output directory |

The resource extraction writes to `part1-results`. The supplied single-document test writes to **`part1-test-results`** and accepts an optional document ID; it does not reset the full dataset table. Both supplied scripts now resolve paths relative to their location or the environment variables above, and check dependencies before clearing outputs.

## Interpreting the evidence

The existing extraction table is based on QDF files. **QDF conversion may renumber objects.** For conclusions about numbering versus object IDs, use the document inspector or generated resource/numbering investigations: they read qpdf JSON from the original PDF and retain the source object references.

A resource prefix is an observation, not proof of a creator or editing. A missing matrix cell (`?`) means no extracted example; the app does not infer that a tool cannot use that resource. `XObject` can include images and forms; inspect subtypes before interpreting it. Sparse evidence is marked with `?` when fewer than the chosen number of distinct documents exhibit a prefix. Matrix counts and observed coverage do not establish conditional consistency by themselves.

Resource tables page through every matching row and export the complete filtered set. For very large documents the inspector shows up to 1,000 resources/numbering groups and 200 reused names with explicit counts; export the full resource evidence or run a numbering investigation for a complete table. Notes are saved in `observations/gui-notes.json`.

## Validation

Run `python3 -m unittest discover -s pdf-analyzer -v`. The seven tests use an isolated fixture dataset and check source object references, local resource scopes and numbering gaps, API filtering/exports, script execution and persistence, cancellation, local request validation, and separation of single-document test results.

Browser workflow checks also covered the real dataset, supplied test script, generated-script execution, original PDF inspection, results tables, the 15-tool matrix, mobile layout, and reduced motion.
