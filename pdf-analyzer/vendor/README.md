# Local browser dependencies

These files are served locally in Docker, native mode and GitHub Pages. PDF exports do not load third-party CDNs.

- Marked 18.1.0: `marked.umd.js`, MIT, [upstream](https://github.com/markedjs/marked); see `marked-LICENSE.txt`.
- DOMPurify 3.4.16: `purify.min.js`, Apache-2.0 OR MPL-2.0, [upstream](https://github.com/cure53/DOMPurify); see `DOMPurify-LICENSE.txt`.

Markdown previews use these bundled libraries without contacting a CDN. HTML is sanitized and remote images are omitted. The Markdown package archives were downloaded from the official npm registry and checked against their registry SHA-1 checksums.

- jsPDF 4.2.1: `jspdf.umd.min.js`, MIT, [upstream](https://github.com/parallax/jsPDF); see `jspdf-LICENSE.txt`.
- jsPDF-AutoTable 5.0.8: `jspdf.plugin.autotable.min.js`, MIT, [upstream](https://github.com/simonbengtsson/jsPDF-AutoTable); see `jspdf-autotable-LICENSE.txt`.
- DejaVu Sans regular and bold: the included TTF fonts support Latin, Greek and Cyrillic evidence text; see `DejaVu-LICENSE.txt`.

The PDF export library archives were downloaded from the official npm registry and their SHA-512 package integrity values verified before these distribution files were copied.
