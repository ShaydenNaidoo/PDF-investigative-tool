# Local PDF export dependencies

These files are served locally in Docker, native mode and GitHub Pages. PDF exports do not load third-party CDNs.

- jsPDF 4.2.1: `jspdf.umd.min.js`, MIT, [upstream](https://github.com/parallax/jsPDF); see `jspdf-LICENSE.txt`.
- jsPDF-AutoTable 5.0.8: `jspdf.plugin.autotable.min.js`, MIT, [upstream](https://github.com/simonbengtsson/jsPDF-AutoTable); see `jspdf-autotable-LICENSE.txt`.
- DejaVu Sans regular and bold: the included TTF fonts support Latin, Greek and Cyrillic evidence text; see `DejaVu-LICENSE.txt`.

The library archives were downloaded from the official npm registry and their SHA-512 package integrity values verified before these distribution files were copied.
