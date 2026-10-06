# PDF Analyzer · Vice Lab

A local COS 721 PDF investigation app with a Vice City inspired synthwave design: neon lights, an animated sunset, palm silhouettes, transitions, click ripples and live run effects. Motion respects your operating system's reduced-motion preference. Interface assets are local; no third-party Python packages are needed. The first Docker build downloads the lab tools; later investigations work locally.

## Open the Docker GUI

Install Docker once using the [installation instructions](../README.md#start-the-docker-lab). In VS Code choose **Tasks: Run Task → Start PDF Analyzer (Docker)**, or open the matching **Start Lab** launcher from the repository root. The launcher installs all lab tools in Docker and opens <http://localhost:8080>.

**Lab setup** shows tool readiness, script counts, exemplar sets, imported PDFs and free disk space. Drop your PDF files or assignment ZIP onto the upload area, then click **Import into lab**. Nested assignment ZIPs are supported. Imports accept files up to 4 GiB each, up to 20,000 PDFs and 8 GiB of expanded archive content, including nested ZIP contents. Import status is visible while processing; keep the page open until the upload completes. If interrupted, restart the lab and retry. Already imported identical PDFs are kept. Files named `.pdf` without PDF content are skipped and listed in the report; valid PDFs in the same ZIP still import.

Click **Build first investigation** to generate a resource investigation for an available PDF. Review it, run it, and inspect the resulting table. **Explore PDFs** opens the evidence explorer. You can return to **Lab setup** to add more PDFs. Imports and investigations run one at a time to keep the evidence inventory consistent.

The included baseline observations contain IDs for the full assignment corpus. Before importing that corpus, the app reports these PDFs as missing. Importing a personal PDF does not invent a tool label; it appears as **Unassigned** in exemplar summaries.

The Docker lab saves PDFs, custom scripts, notes and results in a named volume. Use **Stop PDF Analyzer (Docker)** to stop it; launching again restores your work. See [backup and restart instructions](../README.md#set-up-and-investigate-in-the-browser). Scripts use `/workspace/environment/observations` and `/workspace/dataset` inside Docker. Use the environment variables below when building scripts so they work in either mode. Existing native runs and notes remain in their original local workspace.

## Open the native GUI (optional)

The **Start PDF Analyzer** VS Code task or `python3 pdf-analyzer/server.py --open` opens <http://127.0.0.1:8766>. Keep that task running while using the app. Required local tools are Python 3.11+, Bash, qpdf with JSON v2 support, Poppler (`pdfinfo`, `pdftotext`), awk, sed, grep, find, sort, uniq and column.

Change the port with `--port` if 8766 is occupied. Restart the server after changing its Python files. **Lab setup** also works here and imports into `environment_set/master-gdc-gdcdatasets-2020445568-2020445568/lcwa_gov_pdf_data/data`. Observation scripts, runs and notes stay under `environment_set/environment/observations`.

## Investigate without terminal commands

**Field notebook** and **Document notes** support Markdown with **Read**, **Edit** and **Split** views. Read displays headings, lists, tables, links, blockquotes, task lists and code; Split previews your text as you type. Notes with saved content open in Read mode. **On this page** links jump to headings in longer notes. On small screens, Split stacks the editor above the preview.

In **Field notebook**, choose **Open .md file** to read or edit a Markdown file (up to 2 MiB), including your assignment guide or exported notes. Opening a file changes the editor; choose **Save notes** to keep that text in the lab. Unsaved changes are marked. **Export notes** retains the original Markdown, and existing PDF exports remain available. Markdown rendering works offline; images and executable HTML are omitted from previews.

**Export PDF** downloads complete matching evidence and result tables, comparisons, summary charts/tables and notebooks. In the document dossier, **Export view PDF** exports the selected investigation view. **Export entire run PDF** includes every saved table and full console logs for a completed run.

- **Lab setup:** automatic environment preparation, tool checks, browser PDF/ZIP imports and readiness status.
- **Dashboard:** real dataset counts, resource-prefix frequencies, tool availability, and assignment examples to inspect.
- **Evidence explorer:** searchable documents and resource mappings, tool/type filters, sortable columns, pagination, and CSV exports of all matching rows. Document searches save automatically after a pause in typing, on Enter, or when leaving the search field. **Previous document searches** persists in the same browser across reloads; case and extra spaces do not create duplicates. Click a saved search to reuse it with all tools selected, remove one with **×**, or choose **Clear history**. Resource-mark searches are excluded.
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

Scripts run inside `/workspace/environment/observations` as the container's `lab` user in Docker, or inside `environment_set/environment/observations` with the local account's permissions in native mode. Saved custom scripts are in `observations/gui-scripts`. Each run preserves a copy of its script, stdout/stderr, timestamps, status, exit code, and tables under `observations/gui-runs/<run-id>`. Runs are serialized so assignment scripts cannot concurrently overwrite shared outputs. A run has a 30-minute limit; stopping a run terminates its process group.

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

Run `python3 -m unittest discover -s pdf-analyzer -v`. The 36 tests use isolated fixture data and check source object references, local resource scopes and numbering gaps, API filtering/exports, script execution and persistence, cancellation, local request validation, and separation of single-document test results. They also cover strings offsets and search, exact tags, compressed objects/content, decoded streams, custom metadata and XMP, index limits, and preservation of the original PDF. Summary tests cover full-table aggregation, distinct-PDF counts, filters, coverage denominators, missing IDs, overlapping membership, complete exports, and cache refresh when results or exemplar sets change. They also check capability reporting and rejection of unknown run views and resource columns used as PDF IDs. Google Drive tests verify whole-lab restore, interrupted backups, checksums, credential handling and transfer guards using real rclone with temporary local storage; six tests skip if rclone is missing outside Docker.

Browser workflow checks also covered the real dataset, supplied test script, generated-script execution, original PDF inspection, results tables, the 15-tool matrix, mobile layout, and reduced motion.

The strings/metadata browser checks cover direct document shortcuts, highlighted searches, exact tags, pagination, exports, stream decoding, page text, switching documents during requests, existing resource/numbering views, and mobile layout.

Summary browser checks use the real 130,026-row saved run and cover the three chart measures, bar interactions, filters, breakdowns, pagination, CSV/SVG exports, table switching, unsupported tables, stale responses, empty searches, mobile layout and reduced motion. Its aggregates were also checked against the supplied CSV. The corrected workflow was verified on the default port 8766, including clear handling of an outdated backend response and automatic PDF ID selection.

Setup tests also cover nested assignment archives, duplicate imports, original hash preservation, invalid archives and conflicting IDs, upload authentication, restart seeding without overwriting scripts/notes/results, and Docker environment paths.

Docker verification built the actual image and ran all 24 tests with `TMPDIR=/workspace/home` (the container mounts `/tmp` with execution disabled). Browser checks imported the full assignment ZIP, reported its one HTML file mislabeled as a PDF, ran a saved generated investigation, displayed its exemplar summary and chart, inspected strings/metadata, and checked mobile layout. All 999 imported PDF hashes matched the originals. Container restart preserved PDFs, saved scripts and completed result tables.

The strict-mode Part 1 script regression checks cover empty observation/exemplar sets, zero-overlap prefix counts, qpdf recovery warnings, missing PDFs and unchanged originals. Builder browser checks ran the corrected script on fixture PDFs and verified saved tables, exemplar summaries, expired-token reconnection, duplicate-click prevention, visible startup errors and Run-button recovery when another tab finishes a job.
