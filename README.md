# PDF Analyzer · Vice Lab

A local GUI for COS 721 PDF toolmark investigations, with a synthwave interface, neon effects, script editing, live investigation output, searchable evidence tables, and CSV exports.

Use **Script studio → Investigation results → Generate summary** to summarize a full saved result table across exemplar tools. Compare row counts, distinct PDFs and observed coverage in a table and interactive bar chart; export the summary as CSV or the chart as SVG. See [Summarize a large investigation](pdf-analyzer/README.md#summarize-a-large-investigation).

Click a PDF to use **Strings & tags** for searchable file strings, decoded dictionaries, exact PDF tags, page text, and stream previews. **Metadata** shows document properties, custom Info fields, trailer identifiers, and XMP, with JSON and CSV exports. See [Look inside a PDF](pdf-analyzer/README.md#look-inside-a-pdf) for a walkthrough.

![PDF Analyzer dashboard](pdf-analyzer/preview-desktop.png)

## Start the app

Open this repository's root folder in VS Code. Use **Ctrl+Shift+P → Tasks: Run Task → Start PDF Analyzer**. The task starts the backend and opens <http://127.0.0.1:8766>.

You can also start it with:

```bash
python3 pdf-analyzer/server.py --open
```

The app uses local Python 3, Bash, qpdf with JSON v2 support, Poppler tools such as pdfinfo, and the assignment's shell utilities. It needs no third-party Python packages. See the [app README](pdf-analyzer/README.md) for requirements and usage.

## Dataset setup

The original PDF corpus, assignment PDFs, compressed archives, generated PDF transformations, investigation runs, and personal notes are excluded from Git. Keep those files locally.

After cloning, extract or copy your separately supplied PDF corpus into this layout:

```text
environment_set/
  master-gdc-gdcdatasets-2020445568-2020445568/
    lcwa_gov_pdf_data/
      data/
        <original PDF files>
  environment/
    observations/
      all
      tools/
      marks/
      ...
pdf-analyzer/
.vscode/tasks.json
```

The app resolves its environment relative to the repository root. Keep the `pdf-analyzer` and `environment_set` folders beside each other. The observation scripts and baseline observation sets are included; the PDF corpus is supplied separately.

The dashboard's original-PDF inspector and generated investigations work after the dataset is restored. To populate the resource overview and tool comparison, run **Extract resource marks** in Script studio. Generated results stay local.

The script guide references `assign2.pdf`; add your assignment brief locally if you want that link to work.

## Guides

- [App usage and evidence interpretation](pdf-analyzer/README.md)
- [Detailed script-building guide](pdf-analyzer/README_SCRIPT_BUILDER.md)
- [Copyable investigation scripts](pdf-analyzer/examples/)

## Validation

```bash
python3 -m unittest discover -s pdf-analyzer -v
```

The fifteen tests use an isolated fixture dataset and check original references, resource scopes, filtering and exports, script execution, cancellation, persistence, result isolation, strings and compressed content, custom metadata/XMP, preservation of the original PDF, and full-table exemplar summaries.
