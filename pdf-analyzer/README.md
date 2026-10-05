# PDF Analyzer · Vice Lab

A local COS 721 PDF investigation app with a Vice City inspired synthwave design: neon lights, an animated sunset, palm silhouettes, transitions, click ripples and live run effects. Motion respects your operating system's reduced-motion preference. Assets are local; no internet connection or third-party Python packages are needed.

## Open the GUI

In VS Code, open the Command Palette (`Ctrl+Shift+P`), choose **Tasks: Run Task**, then **Start PDF Analyzer**. The task starts the backend and opens your browser at <http://127.0.0.1:8766>. Keep the task running while using the app.

The backend can also be launched with `python3 pdf-analyzer/server.py --open`. Change the port with `--port` if 8766 is occupied. Required tools are `bash`, `qpdf` with JSON v2 support, `pdfinfo`, `pdftotext`, `awk`, `sed`, `grep`, `find`, `sort`, `uniq`, and `column`. Your environment already provides these. Restart the server after changing its Python files; refreshing the browser alone does not reload the backend. If an older backend is already running, the launcher tells you to stop the existing task and start it again. Reusing an existing server leaves saved run records unchanged.

## Investigate without terminal commands

- **Dashboard:** real dataset counts, resource-prefix frequencies, tool availability, and assignment examples to inspect.
- **Evidence explorer:** searchable documents and resource mappings, tool/type filters, sortable columns, pagination, and CSV exports of all matching rows.
- **Document inspector:** open the original PDF, search strings and tags, view complete document metadata and XMP, inspect resource subtypes, local resource scopes, original object definitions and decoded streams, numbering gaps, name reuse, existing marks, and document notes.
- **Tool comparison:** prefixes by resource type for all 15 exemplar tools, with distinct-document counts and a configurable sparse-evidence threshold. Export the matrix to CSV.
- **Script studio:** run observation scripts, generate investigations from controls, edit/save Bash scripts, inspect live output and errors, stop runs, reopen history, filter result tables, and generate exemplar summaries with tables, interactive bar charts, CSV and SVG exports.
- **Field notebook:** save reasoning and document notes and export them together as Markdown.

## Build your own investigation scripts

Read the [Script Builder README](README_SCRIPT_BUILDER.md) for the full GUI walkthrough, scope/filter rules, Bash and Python examples, result-column definitions, TSV output format, original-object inspection, and troubleshooting. Copyable scripts are in [`examples/`](examples/).

## Look inside a PDF

Click a document ID or **Inspect** to open its dossier. Document rows also have **Strings** and **Metadata** shortcuts.

In **Strings & tags**, choose a content view:

| View | What it shows | Useful searches |
| --- | --- | --- |
| File strings | Printable ASCII from the original file, with hexadecimal byte offsets and a configurable minimum length | `/Producer`, `/Creator`, `%%EOF`, resource names |
| PDF objects & tags | Readable dictionaries, including objects stored in compressed object streams, with original object references | `/Font`, `/XObject`, `/Metadata`, `/TT2` |
| Page text | Text extracted by `pdftotext`, grouped by page | Words appearing in the document |

Type in the search box to highlight matching text. **Match case** controls case sensitivity. In the objects view, click a tag chip or choose an exact tag from the dropdown; this filters actual PDF names rather than incidental text inside string values. Text search and the tag filter can be combined. **Clear** resets both filters. The dropdown includes all indexed tags; the chips show the 35 most frequent.

Choose **Inspect object** to see its definition, or **Decode stream** to read a stream's decoded contents. The preview offers definition/stream switching and TXT export. Decoded streams can include PDF drawing instructions, XMP XML, or binary data; they are displayed as text, with unreadable bytes replaced. **Export matches TXT** and **CSV** export all matching indexed records, including records outside the current results page.

Raw strings cannot reveal compressed content. Use the objects view and stream decoding for that. Page text does not perform OCR, so image-only PDFs may show no text. The objects view is a readable reconstruction from qpdf JSON, with original references; it does not preserve original whitespace.

In **Metadata**, search document properties, the original Info dictionary (including custom fields), trailer identifiers, and catalog XMP. Click the original Info or XMP reference to inspect that object. **Export JSON** includes the metadata and XMP preview; **CSV** exports the properties, Info fields and trailer fields. Metadata exports include all these fields regardless of the search box.

Inspection reads the original PDF without rewriting it. Strings indexing is bounded to 100,000 records or 16,000,000 characters; page text extraction is bounded to 16,000,000 bytes. The interface reports when an index is incomplete, and searches/exports then cover only that indexed portion. Each visible record previews up to 8,000 characters, with longer matching records available in the strings exports. Object and decoded-stream previews, including XMP and their exports, are capped at 2,000,000 bytes with a visible notice.

## First investigation

1. Open **Script studio → Build a script**.
2. Choose **Resource names & original references** or **Numbering & gaps by local scope**.
3. Enter a document ID, for example `22ZOC` or `GGGXC`. Enter several IDs separated by commas. Clear the IDs to investigate all documents, or select an exemplar tool to limit the scope.
4. Optionally choose a resource type and exact prefix.
5. Click **Generate script**, review/edit it, then **Run investigation**.
6. Scroll to **Investigation results**, filter the evidence, and click **Export CSV**. Click any document ID to inspect the PDF.

The script library includes `part1_resources.sh`, `test_part1.sh`, the vector/bag/feature/class builders, and set operations. One-document helpers accept an ID, one-tool helpers accept `pr01` through `pr15`, and set operations accept paths such as `tools/pr01 tools/pr02`. Build the four classification stages in order: vectors, bags, feature vectors, classes. They use the existing marks; resource marks are not automatically added to that classification pipeline.

`scan_resources.sh` is excluded and has not been changed.

## Summarize a large investigation

1. Open **Script studio**, finish a run or select an existing run in **Run history**.
2. In **Investigation results**, choose the detailed table, such as `all-resources.tsv`, then click **Generate summary**. Summary generation reads every row in that saved table, including rows outside the displayed results page.
3. Choose the **PDF ID column** and **Table breakdown**. Tables using `document`, `document_id`, `pdf`, or `id` are detected automatically. When one such column is present, it is selected and fixed so resource prefixes cannot accidentally be treated as PDF IDs. Choose **By tool · overall**, a single result column, or **Resource type + prefix** when those fields are present.
4. Filter by exemplar tool or resource type. The results search box also filters the summary; clear it to summarize the full table. Summary filters leave the raw result table available above.
5. Switch the chart measure between **Distinct PDFs**, **Result rows**, and **Observed coverage (%)**. Click a bar or a tool in the summary table to filter to that tool; click it again to clear the tool filter. Bars also respond to Enter/Space.
6. **Export summary CSV** exports every matching summary group, including groups outside the summary page. **Save chart SVG** exports the current graph as a standalone image suitable for an assignment; its SVG description records the run, table, filters and counts.

The table shows the exemplar tool, producer label, chosen breakdown, result-row count, distinct PDF count, number of known exemplars, PDFs represented in the full source table, and observed coverage. Tool membership comes from the current `observations/tools/pr*` files; producer labels use the most common recorded producer in each set. Summary generation does not rerun or change your investigation script.

**Result rows** count entries, including duplicates or repeated resource scopes. **Distinct PDFs** count each document once per tool/category, so adding resource categories can double-count documents. **Observed coverage** is matching PDFs divided by all known exemplars for that tool. **PDFs in source** counts tool members represented before applying filters, which helps distinguish missing source evidence from a search with no matches. Zero results do not establish that a tool cannot produce a resource or prove editing. This feature counts rows and PDFs; it does not sum numeric columns from custom scripts.

PDFs without exemplar membership appear as **Unassigned**, with coverage unavailable. They remain in the summary table and totals; use **Include unassigned PDFs in the chart** to add their bar. Rows without PDF IDs contribute to row counts only. If a PDF belongs to several exemplar sets, it contributes to each and the interface reports overlap.

For the supplied `14a7b9bef915-all-resources.csv`, reopen **part1-investigation** (`14a7b9bef915`) and choose `all-resources.tsv`; its saved table matches that export, so a rerun is unnecessary. This source contains 130,026 rows across 886 PDFs: 294 have exemplar membership and 592 are unassigned under the current tool sets. Already aggregated tables such as `prefix-summary.tsv` lack individual PDF IDs; choose the detailed table to summarize across exemplars.

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

Run `python3 -m unittest discover -s pdf-analyzer -v`. The fifteen tests use an isolated fixture dataset and check source object references, local resource scopes and numbering gaps, API filtering/exports, script execution and persistence, cancellation, local request validation, and separation of single-document test results. They also cover strings offsets and search, exact tags, compressed objects/content, decoded streams, custom metadata and XMP, index limits, and preservation of the original PDF. Summary tests cover full-table aggregation, distinct-PDF counts, filters, coverage denominators, missing IDs, overlapping membership, complete exports, and cache refresh when results or exemplar sets change. They also check capability reporting and rejection of unknown run views and resource columns used as PDF IDs.

Browser workflow checks also covered the real dataset, supplied test script, generated-script execution, original PDF inspection, results tables, the 15-tool matrix, mobile layout, and reduced motion.

The strings/metadata browser checks cover direct document shortcuts, highlighted searches, exact tags, pagination, exports, stream decoding, page text, switching documents during requests, existing resource/numbering views, and mobile layout.

Summary browser checks use the real 130,026-row saved run and cover the three chart measures, bar interactions, filters, breakdowns, pagination, CSV/SVG exports, table switching, unsupported tables, stale responses, empty searches, mobile layout and reduced motion. Its aggregates were also checked against the supplied CSV. The corrected workflow was verified on the default port 8766, including clear handling of an outdated backend response and automatic PDF ID selection.
