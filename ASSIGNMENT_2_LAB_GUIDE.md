# COS 721 Assignment 2: collect the evidence with PDF Analyzer

This is a working guide, not a completed assignment answer. It maps the requirements in [assign2.pdf](assign2.pdf) to your lab's controls and evidence exports. Read the specification yourself and write your own conclusions. The [environment README](environment_set/environment/README.pdf) describes the supplied research workbench; it is not an additional assignment marking rubric.

**Due:** Monday, **12 October 2026**, on **clickUP**. The assignment contributes **30% of the semester mark**. Parts 1, 2 and 3 each receive an impression mark out of 10. The spec explicitly says the informed discussion matters more than the prefix table or descriptions of numeric patterns. This is an individual assignment, and steganalysis earns no marks.

## What you need to finish

| Spec requirement | Evidence to collect | Where this guide covers it |
| --- | --- | --- |
| Part 1: naming prefixes for all 15 exemplar tools; sparse/absent cases; combine tools sharing conventions; discuss consistency and discrimination | Original resource names, categories/subtypes, exemplar membership, distinct-document counts, a compact tool-by-type table and concrete examples/counterexamples | Steps 3–5 |
| Part 2: starts, increments, meaningful skipped values, local name reuse and whether targets are the same; discuss classification value | Scope-specific suffix sequences, original object references, reuse across distinct resource dictionaries and enough increments to support each inference | Steps 6–7 |
| Part 3: what deviations mean for a proposed convention, attribution or possible editing | MM5SP/MZRWQ/GKMDO/GGGXC comparisons, metadata, original object definitions and alternative explanations; optionally a controlled edit | Steps 8–9 |
| Examples: CUF7M, QZ74K and the assignment PDF itself may change your conclusions | Font names/definitions; Page versus Form contexts; `/ProcSet`; metadata/trailer IDs; the assignment PDF's resources | Steps 10–12 |
| Submission: four marked pages, A4 PDF, 12pt primary font, name printed inside, monochrome | A concise report built from your verified observations, plus a private evidence archive | Steps 13–14 |

The main brief is section 2 (printed pages 2–6), marking guidance is section 3 (page 6), examples are section 4 (pages 6–9), and submission rules are section 5 (page 9).

## Step 1 — Open the correct lab and confirm the inputs

1. Start Docker, then open **Start Lab** or choose **VS Code → Tasks: Run Task → Start PDF Analyzer (Docker)**.
2. Open **http://localhost:8080**. Use **Lab setup** to confirm that the required tools are ready and the 15 exemplar sets are present.
3. If necessary, choose the assignment corpus ZIP and click **Import into my lab**. The outer ZIP containing `lcwa_gov_pdf_data.zip` is supported. Keep the page open during upload.
4. Check the import report. Your supplied corpus contains one HTML file named `6HTC5FVAQW3DVHYRD7PVJGBBQS7GRZTL.pdf`; the Docker importer reports and skips it. **999 available PDFs and one missing observation ID are expected for that import.** Keep a note of this rather than reporting that every corpus file parsed successfully.
5. In **Evidence explorer**, search for `CUF7M`, `QZ74K`, `GGGXC`, `MM5SP`, `MZRWQ` and `GKMDO`, and confirm they are available.
6. Use one workspace throughout this workflow. The native app at **http://127.0.0.1:8766** has separate scripts, notes and run history. Its old runs are not automatically copied into Docker.

You do not need to run **Build document vectors → Build exemplar bags → Build feature vectors → Build induced classes** before investigating resource names. Those scripts reproduce the companion workbench's existing mark-based classification. They do not discover new resource conventions or automatically classify newly imported PDFs.

## Step 2 — Set up your evidence notebook and saving routine

1. Open **Field notebook** and create headings for **Part 1**, **Part 2**, **Part 3**, **CUF7M**, **QZ74K**, **Assignment PDF**, and **Methods/limitations**.
2. For every investigation, record the script name, run ID, selected tool/document IDs, filters, run status, warnings and exported filenames.
3. In a folder on your computer, keep exported evidence under `part1/`, `part2/`, `part3/`, `examples/` and `methods/`. These are your working records; they do not all have to fit in the report.
4. After each run, select each useful table in **Investigation results**, clear the result search for a full export, then click **Export CSV**. A filtered export contains only matching rows.
5. Save useful object-definition/stream TXT exports, metadata JSON/CSV exports, and focused screenshots. Keep the PDF ID and original reference visible in screenshots.
6. Save a copy of the exact script code in your methods folder before changing it; the lab also freezes the executed code in each run. Save document notes from its inspector, and export your **Field notebook** as Markdown periodically.

Use this record structure for every proposed convention:

| Field | What to record |
| --- | --- |
| Tool and version/label | `prNN`, exemplar set, and the producer/creator evidence behind the label |
| Locus and condition | Resource type, Page/Form/other context, and whether that resource is declared or actually used |
| Candidate convention | Your proposed prefix/number/reuse behaviour |
| Supporting evidence | PDF IDs, scope IDs, original names and references, and distinct-document counts |
| Counterexample | The conflicting PDF and precise context, or the scope of the search if none was found |
| Interpretation | What the observations support, the alternatives, and whether the convention separates tools |

## Step 3 — Collect the original-PDF evidence once

Use the companion [assignment2-evidence.sh](pdf-analyzer/examples/assignment2-evidence.sh). It reads the original PDFs through the lab helper and records resource scopes, numbering, reuse, metadata, hashes, declared-kind prefix counts and Page/Form context. It writes only to the current run's output folder.

1. Open the linked script in VS Code and copy **the whole file**, including its Python heredoc. Do not copy Markdown backticks.
2. In the app choose **Script studio → Build a script** and paste it into the editor.
3. For a small first run, change the two lines near the top to:

   ```bash
   export A2_TOOLS="pr01"
   export A2_DOCUMENTS=""
   ```

4. Set **Script name** to `a2-pr01-evidence`, save, and run. Wait for **COMPLETED** and exit 0.
5. Verify the expected tables below appear. If it fails, inspect **Live output** and `failures.tsv`; a failed run's other tables can contain partial evidence.
6. After checking that sample, change the lines to:

   ```bash
   export A2_TOOLS="all"
   export A2_DOCUMENTS="CUF7M,QZ74K,GGGXC,MM5SP,MZRWQ,GKMDO"
   ```

7. Rename the script `a2-all-evidence`, save, and run. It examines the union of the 15 exemplar sets and those six named cases, not every unassigned PDF in the corpus. A PDF in multiple selected sets is inspected once, and its membership is recorded.
8. Export all relevant tables. If the full run reaches the lab's 30-minute limit, use smaller scopes such as `pr01,pr02,pr03`, with `A2_DOCUMENTS=""`; run the six named cases separately with `A2_TOOLS="none"`.

| Table | Use |
| --- | --- |
| `inventory.tsv` | Selected IDs, exemplar membership, input filenames/SHA-256 hashes and inspection status |
| `resources.tsv` | Names, suffixes, resource types, Image/Form subtypes, original references, scopes and contexts |
| `prefix-evidence.tsv` | Per-tool prefixes with distinct-PDF counts, inspected/expected exemplars and a denominator restricted to PDFs declaring that resource kind |
| `numbering.tsv` | Per-PDF/type/prefix/scope minimum, maximum, distinct suffixes, gaps and object-number matches |
| `reuse.tsv` | Exact names declared in multiple distinct scopes and their same/different original target references |
| `contexts.tsv` | Original owners, Page/Form/Pages context, inherited resource declarations, `/Contents` references, `/ProcSet` and form bounding boxes |
| `metadata.tsv` | Current `pdfinfo` producer/creator, version, page count and dates; use the inspector for complete Info/XMP/trailer details |
| `tool-membership.tsv` | Snapshot of the selected exemplar sets for the evidence run |
| `failures.tsv`, `warnings.tsv` | Missing/unreadable files, inspection errors and recovery warnings |
| `versions.tsv` | Versions of the tools used for that run |

**Check completeness before interpreting:** for each selected tool, compare `inspected_exemplars` with `expected_exemplars`, and inspect failures. An empty `prefix-evidence.tsv` row for a type is not an N/A decision. The context collector covers top-level Page/Form resource dictionaries and Page inheritance; use object inspection for unusual nested structures. A scope shared by several owners may have several listed contexts, and the raw helper's `owner` is only a representative owner.

The older **part1-investigation-fixed** script is useful for its Bash/QDF extraction, but **do not use its QDF object numbers for Part 2 or Part 3 object-identity claims**. Conversion can renumber objects. A custom run also does not automatically populate the Dashboard/Tool comparison resource overview: inspect its own saved tables and summaries.

## Step 4 — Build the Part 1 prefix table

1. Select `resources.tsv`, clear the result search, and click **Generate summary**.
2. Use **PDF ID column = document** and **Table breakdown = Resource type + prefix**. Leave resource/tool filters clear initially.
3. Use **Distinct PDFs** for the bar chart, then export the summary CSV and chart SVG. Named cases appear as **Unassigned** because they are outside the supplied tool sets; do not treat that label as a creator tool.
4. Select `prefix-evidence.tsv`. Read/export this table directly; it is already aggregated and has no individual PDF IDs. Do not run an exemplar summary on it.
5. For each `pr01` through `pr15`, inspect the prefixes by resource kind. `XObject:Image` and `XObject:Form` are separate. The built-in **Tool comparison** column `XObject` combines both, so that column alone cannot establish an image-only convention.
6. Build your report table using columns such as **Font**, **Image**, **Form**, **ColorSpace**, **ExtGState**, and other supported types where relevant (`Pattern`, `Shading`, `Properties`). Retain meaningful static names such as `/Helv`; their numeric suffix is absent.
7. For every nontrivial cell, keep at least one supporting PDF/scope/reference in your working notes. Record every conflicting prefix, then inspect whether it belongs to another context, an unused declaration, a different subtype, or a genuine unexplained inconsistency.

Use the spec's notation carefully:

| Cell | When to use it |
| --- | --- |
| `/F` or another prefix | A supported convention in the condition/context you investigated |
| `/Image?` | A tentative prefix based on very few distinct exemplar documents; explain which tool is sparse |
| `?` | A resource type may be possible, but the exemplars provide no observed example |
| `N/A` | You have independent grounds that the tool cannot use that resource type; absence from these exemplars alone is insufficient |
| More than one prefix / a note | Keep the observed alternatives and their contexts visible rather than choosing a favourite |

The GUI's adjustable sparse threshold is a display aid, not a threshold specified by the assignment. Explain any threshold you choose in your working method. Compare tools across the whole proposed convention, then combine rows only when the evidence supports it. Preserve sparse qualifications in numbered notes when combining a confident cell with a tentative one, as the spec requests.

### Read the denominators correctly

Suppose a tool has 23 exemplars, only 2 declare images, and both use one image prefix. The GUI's **Observed coverage** is `2 / 23`; the companion table's **declared-kind coverage** is `2 / 2`. The former describes prevalence in the exemplar set, and the latter supports a conditional hypothesis among declarations. Neither establishes that an image is actually drawn: inspect a representative page/form content stream for its `/Name Do` use. Likewise, a font declaration is not proof that text uses it; inspect `/Name ... Tf` where relevant.

You do not need to turn every resource into a content-stream study. Verify use when your inference depends on a declaration actually being used, and state the scope of what you checked.

## Step 5 — Write the evidence-based Part 1 discussion

For each potentially useful convention, answer:

1. In which condition is the prefix consistent? Give tool IDs, concrete PDF evidence and observed conflicts.
2. Which other tools share it, and which differ? A shared prefix can separate groups; it need not identify exactly one tool.
3. Does the convention concern a Page, Form, inherited dictionary or another context?
4. Do CUF7M or QZ74K require you to qualify the proposed rule?

The spec specifically discourages generic discussion of dataset size, and `?` already expresses an unobserved case. Spend the scarce report space on the actual observations and classification implications.

## Step 6 — Investigate Part 2's suffix sequences

1. Select `numbering.tsv` from the same original-PDF run.
2. Start with one tool's PDFs using `inventory.tsv`/`tool-membership.tsv` and its resource rows. If you want a smaller GUI-generated run, choose **Numbering & gaps by local scope**, select `prNN`, **clear Document IDs**, leave type/prefix filters blank, then **Generate script → Save → Run**.
3. Look for groups with at least three distinct numeric suffixes, and for two separate sequences containing two consecutive suffixes each. These are possible sources of the spec's two increments.
4. Verify the actual ordered names in `resources.tsv`; sort suffixes numerically. Keep document, resource type and scope together. Do not combine unrelated scopes or PDFs into a single sequence.
5. Record the observed minimum, increments, skipped values and the scopes where they occur. Check across exemplars before calling a start value a tool convention.
6. Open conflicting PDFs and inspect the owning dictionaries and original targets. Classify the conflict as explained by context, a meaningful pattern, or still unresolved.

`start` is the **lowest observed suffix**, not proof of the first resource ever created. Blank `missing_between` means no missing number between the observed minimum and maximum; a one-resource group also has no internal gap. A minimum of 4 does not by itself establish that names 0–3 existed and were removed. Static names and compound names need separate treatment: `/C2_0` is mechanically split into prefix `/C2_` and suffix `0`, which need not describe the tool's semantic naming scheme.

Before asserting incremental numbering under the spec's sparse-evidence allowance, verify all four conditions:

- [ ] A common starting point for the resources considered.
- [ ] Incremental numbering from that point.
- [ ] No skipped values in the supporting sequences.
- [ ] At least two observed increments: for example three consecutive names of one type, or two separate two-name sequences of two types.

These are conditions from the spec, not an automatic conclusion produced by the numbering table. Do not spend report space merely saying that a singleton such as `/CS0` is insufficient. The Ghostscript `/R` plus object-number idea is already supplied in the spec and earns no marks for repetition; use it as a check or document a specific counterexample if you find one.

## Step 7 — Investigate Part 2's name reuse and discrimination

1. Select `reuse.tsv`. Each row represents the **same exact name and resource type in one PDF**, declared in at least two distinct resource scopes.
2. Read `scopes`, `targets` and `relation`. A shared dictionary used by two pages is one declaration scope, not two independent redeclarations.
3. For **same original object**, inspect the actual target definition. For **different original objects**, inspect both targets; distinct references need not mean visibly different fonts/images, so compare the definitions as well.
4. For direct values, inspect the definitions rather than treating the word `direct` as a shared object identity.
5. Verify GGGXC specifically: locate `/F13` in the contexts described in the spec (objects 9 and 26) and follow the target reported as object 28. Save your own original-resource/object exports rather than relying on the spec's description as your experimental evidence.
6. Compare observed starts, skips and reuse policies across tools. Identify concrete examples that separate two tools/groups, and examples where the convention is shared or ambiguous.

Object references can be compared **within one PDF**. Object 28 in another document has no shared identity with it. Nor does an object number in a rewritten PDF automatically identify its pre-edit counterpart.

For an object not shown by a convenient button, use **Strings & tags → PDF objects & tags**, find its original reference and choose **Inspect object**. Alternatively paste [inspect-original-object.sh](pdf-analyzer/examples/inspect-original-object.sh) into the editor, change its `document` and `object_reference`, save under a new name, and run. For `28 0 R`, the script's reference is `28,0`.

## Step 8 — Collect Part 3's attribution/deviation evidence

Use `MM5SP`, `MZRWQ`, `GKMDO` and `GGGXC` from the named-case run. Set the builder's **Exemplar tool = All documents** for any individual run: these named cases are not in the supplied exemplar sets, and intersecting them with `prNN` can return an empty result.

For **each** case:

1. Open its **Metadata** view and export **JSON** and **CSV**. Record current Producer/Creator, dates, custom Info fields, catalog XMP and trailer `/ID` values where present. The producer label in an old observation file is a separate source from the current original's metadata.
2. Save its original resource rows and numbering groups from the evidence bundle.
3. Compare numeric suffixes with original target numbers. `suffix_equals_object` is a match count; use `numeric_indirect_entries` or the underlying rows as the relevant denominator, and inspect every exception relied on in your report.
4. Inspect supporting target definitions and owning scopes. For MM5SP, verify the spec's `/F14` and `/Im13` examples yourself. For GKMDO, verify `/F12` and its target in object 20.
5. For the producer named in MZRWQ, find additional corpus examples and inspect their patterns. To find candidates through the GUI, search **Evidence explorer** using a distinctive producer substring, then confirm each candidate's current metadata. Similar names/versions alone do not establish identical tool behaviour.
6. Compare visual scan-like text versus actual font/text/image structure where relevant. Visual fuzziness or crispness is contextual evidence, not a creator identification on its own.
7. Record alternative explanations: a different producer version, imported forms/pages, inherited or unused declarations, rewriting/renumbering, changed metadata, or an unresolved deviation. Record what further evidence would distinguish them.

Use a comparison sheet like this; fill it with your own observations:

| PDF | Current metadata | Names and original targets | Context/structure | Deviation from proposed rule | Supported interpretation and alternatives |
| --- | --- | --- | --- | --- | --- |
| MM5SP |  |  |  |  |  |
| MZRWQ |  |  |  |  |  |
| GKMDO |  |  |  |  |  |
| GGGXC |  |  |  |  |  |

The spec asks for a broader reflection, not separate answers to every rhetorical question in this example. Explain how you inferred a convention without defining every counterexample away as “edited.” Missing metadata is not proof of scrubbing or editing; the spec supplies the scrubbing history for GGGXC, but that does not establish the history of other PDFs. Different `/ID` values are an observation to investigate, not conclusive proof of a particular edit or editor. The “eight inserted objects” suggestion is explicitly speculative until you have supporting evidence.

## Step 9 — Optional: perform a controlled page-removal experiment

This can help answer Part 3; the spec also permits limited experiments to resolve uncertain conventions. It is not a substitute for examining the supplied corpus.

1. Choose an original with at least three pages and a resource demonstrably used only on a page you will remove. Use **Open PDF**, the original resource scopes, and the relevant content streams to establish that condition first.
2. In **Build a script**, run a controlled experiment that writes a new PDF under `$PDF_RUN_DIR`. Keep the corpus original unchanged. A tested GUI-ready example is [assignment2-page-removal.sh](pdf-analyzer/examples/assignment2-page-removal.sh); change its `A2_SOURCE_ID` before running.
3. The example keeps page 1 and pages 3 onward. Export its `before-resources.tsv`, `after-resources.tsv`, `before-numbering.tsv`, `after-numbering.tsv`, object-definition tables, page-reference text tables and experiment record. Check its hashes, qpdf version and page-count changes.
4. Compare both the remaining names and their definitions. Do resource declarations remain even if their page/use vanished? Are names retained while object numbers change? Are resources pruned or renumbered? Record the actual result.
5. A derivative is labelled separately in these tables and is not automatically imported into the original-PDF inspector. Read the derivative's exported definitions/page-reference tables; the saved `edited.pdf` remains in that run's storage. Do not click an original document and assume you are viewing the edited copy.
6. A known qpdf transformation demonstrates that transformation's behaviour. It cannot establish which historical operation produced a corpus anomaly. For comparisons between editing tools, repeat under controlled conditions with another tool you actually have, and record its version/settings.

If you create a controlled PDF with Word or another creator, record the exact tool/version, export options and intended fonts/images/features, then import it through **Lab setup**. Keep it labelled experimental and outside the supplied exemplar sets. Its appearance in **Unassigned** is expected. Do not merge modern experimental behaviour into the old corpus tool's rule without explaining the version and context differences.

## Step 10 — Investigate CUF7M and revisit your rules

1. Open CUF7M and inspect/export all original font rows. Clear tool filters.
2. Compare its `/F` and `/TT` families, their actual suffix sets and their scopes. Check the spec's described ranges and `/TT` gaps rather than copying them as your results.
3. Inspect several target font definitions and names, including outlying or unusual ones. **Strings & tags** is useful for `/BaseFont`, `/FontDescriptor` and embedded font-stream references; a raw string hit alone does not establish a font resource.
4. The spec mentions `pdffonts`. To save its listing through the GUI, paste and run the following with a script name such as `a2-cuf7m-fonts`:

   ```bash
   #!/usr/bin/env bash
   set -euo pipefail
   pdf="$(find "$PDF_DATASET_DIR" -type f -iname 'CUF7M*.pdf' -print -quit)"
   [[ -n "$pdf" ]] || { echo 'CUF7M is missing' >&2; exit 1; }
   status=0
   pdffonts "$pdf" || status=$?
   exit "$status"
   ```

   This produces a generic line/result table whose CSV preserves the listing. It is a font inventory, not a mapping of all local names to scopes.

5. Decide whether the mixed names undermine a binary “this tool uses F or TT” rule, reflect distinct contexts/components, support an editing hypothesis, or remain unresolved. Give evidence for your choice and record competing interpretations.
6. Update the Part 1/2 discussion if required. For a large PDF, use full exported tables and explicit truncation notices; the inspector's first visible rows are not necessarily the entire evidence.

## Step 11 — Investigate QZ74K by context, not just by document

1. Filter `contexts.tsv` to QZ74K. Locate owners **1, 5, 8 and 60** and Page owners such as **4, 7, 10 and 13**. Inspect `/Type`, `/Subtype`, `/Resources`, `/Contents`, `/BBox` and references yourself.
2. Compare `/TT0` in the distinct contexts of objects 1, 5 and 60. Follow the original target references and compare the actual font definitions/embedding evidence. Do not assume the same name denotes the same font.
3. Compare all resource families in those contexts, including `/CS`, `/GS`, `/Im`, compound font names such as `/C2_0`, and the Form in object 8 with `/F`, `/Image` and its graphic states.
4. A Form XObject's own stream contains its drawing/text instructions; absence of a `/Contents` key on a Form is not evidence that its fonts are unused. Decode the Form stream and trace its invocation from the Page when use matters. Follow the Page-level `/Xf1`…`/Xf4` Form references and `/img` image references. The spec describes three Forms, then sixteen image pages, then a final Form; check the actual Page-to-XObject mapping. A Form has its own resource context, even though it is invoked by a page.
5. Inspect `/ProcSet` in those Form resource dictionaries and the Page resource dictionaries. `contexts.tsv` records resolved declarations; save original definitions too. It does not reproduce original whitespace.
6. Use **Strings & tags → PDF objects & tags** for dictionary searches; use **File strings** only when the original bytes are actually readable. Object reconstruction and QDF output cannot establish original spacing, and compressed dictionaries may not be visible in raw strings.
7. Compare the trailer `/ID` entries through **Metadata**, but keep them alongside structural evidence and alternative explanations.
8. Explain whether the apparent mixture is better described by context-specific conventions, multiple components/editing, unresolved inconsistency, or another supported explanation. Then revisit your Parts 1–3 claims.

The spec's displayed object excerpt is an illustration, not a replacement for your original-PDF inspection. Use current parser warnings and original definitions when the actual file representation differs from the excerpt.

## Step 12 — Investigate the assignment PDF itself

The third explicit example is **this assignment**, stated to have been created with LaTeX and compiled with **xelatex**. It is not one of the 15 supplied exemplar sets.

1. In **Lab setup**, import the local `assign2.pdf` file. Note the document ID displayed by the app; for this filename it is normally `ASSIG`. If an ID conflicts, rename a copy through your file manager to a unique five-character prefix, such as `SPEC2-assignment.pdf`, and import that copy.
2. Paste the evidence script again, using:

   ```bash
   export A2_TOOLS="none"
   export A2_DOCUMENTS="ASSIG"
   ```

   Replace `ASSIG` with the actual ID shown by your app. Save as `a2-assignment-pdf` and run.

3. Export its resources, numbering, contexts, metadata and relevant reuse evidence. Inspect representative font targets and Page/Form context in the GUI.
4. Compare its observations with the generalisations you developed. Treat it as a separate known-production example; do not invent a sixteenth supplied exemplar class or assume its patterns represent every xelatex document.
5. Record whether it makes you revise a claim, distinguish contexts, or retain a claim with an explicit scope.

Import adds the ID to the lab's document list, so the lab may then show more than the corpus's original 1,000 observation IDs. Keep original corpus, imported assignment and controlled experiments distinct in your records.

## Step 13 — Choose the evidence that deserves report space

Use the complete working tables to choose compact, representative examples and meaningful exceptions. Do not paste enormous CSVs, neon dashboard screenshots or every plot into four pages.

A possible page plan—not a requirement imposed by the spec—is:

| Space | Content |
| --- | --- |
| Page 1 | Brief method, combined prefix table, and Part 1's specific consistency/discrimination discussion |
| Page 2 | Part 2's useful starts/increments/skips/reuse evidence and tool comparisons |
| Page 3 | Part 3's pattern/deviation reasoning, original references, metadata and alternatives |
| Page 4 | Integrate the CUF7M/QZ74K/assignment examples, any controlled experiment, and the revisions/qualifications to your conclusions |

The examples can also be integrated into each part rather than isolated on the last page. Balance the three equally weighted parts. If a chart is less informative than a compact table or object-reference example, omit it. Make any chart understandable in black and white through labels/patterns, not cyan versus pink.

For each principal conclusion, ask: **Which exact observation supports it? What contradicts it? What condition/context limits it? Which tools or groups does it actually distinguish?**

## Step 14 — Final evidence and submission checklist

### Evidence collected and interpreted

- [ ] All `pr01`–`pr15` exemplar sets were considered; failures and sparse/absent categories were accounted for.
- [ ] Prefix table distinguishes appropriate resource kinds, tentative observations, unknowns and justified N/A cases.
- [ ] Combined tool rows retain differences in certainty through notes.
- [ ] Part 1 discusses conditional consistency and discrimination using concrete examples.
- [ ] Part 2 covers observed starts, increments, meaningful skips and same/different-target name reuse.
- [ ] Incremental claims satisfy the spec's stated conditions; Ghostscript's supplied observation is not merely repeated for credit.
- [ ] Part 3 examines the named pattern/deviation cases and avoids circular or unsupported editing claims.
- [ ] CUF7M, QZ74K and the assignment PDF were inspected and their impact on your inferences considered.
- [ ] Original references, resource scope, Page/Form context and declaration-versus-use distinctions were preserved.
- [ ] Run IDs, scripts, membership snapshots, hashes, versions, warnings, full exports and notebook records are saved privately.

### Report ready to upload

- [ ] Your own individual analysis; no steganalysis substituted for the requested work.
- [ ] **A4 PDF**, **12pt primary font**.
- [ ] Your **name appears inside the report**, not just in its filename.
- [ ] All assessed reasoning fits in the **first four pages**; only those four are marked.
- [ ] Readable when printed **monochrome**; no conclusions depend on neon colours.
- [ ] If used, at most **two additional pages of addenda**; they are not marked, so no essential argument is left there. Optional references may occupy addenda space.
- [ ] Upload to the Assignment 2 slot on **clickUP by Monday, 12 October 2026**. The supplied spec does not state a time of day; use the time shown in the actual upload slot.
- [ ] Confirm the uploaded file opens, contains your name and is the intended final version. The spec permits resubmissions; the final submission is assessed.

## Common problems during this workflow

| Problem | Check |
| --- | --- |
| One tool run returns no rows | Clear the default `22ZOC` Document IDs field; a tool + unrelated document filter produces an empty intersection |
| A named example disappears from a tool summary | It is outside the exemplar sets; use All documents or the evidence script's named-document selection |
| Dashboard/Tool comparison has no resource data | Custom run outputs do not refresh that shared QDF overview; use your run's original-resource tables/summary |
| Prefix coverage appears unexpectedly low | GUI coverage uses all known exemplars; compare with the declared-kind denominator before making a conditional claim |
| “No gaps” appears on one resource | One number has no internal gap; it does not establish an incremental sequence |
| Reused name appears to have the same target | Compare full references within that PDF and confirm distinct declaration scopes; shared dictionaries and direct values need care |
| Script exits 1 after useful output | Inspect failure tables and Live output; grep no-match under strict mode can also cause this in older scripts |
| FAILED but tables are present | Outputs may be partial; record which documents/stages failed before interpreting them |
| Object numbers disagree with an old table | Verify the original-PDF evidence rather than numbers in a QDF conversion |
| Imported experimental PDF lacks a tool label | It remains Unassigned until you deliberately define membership; do not alter the supplied sets just to get a chart label |
| Run cannot start after an app update | Refresh with Ctrl+Shift+R; the updated builder can also reconnect an expired lab token |
| Want to preserve a manually edited script | Save first; **Generate script** replaces the current draft. Changing controls without generating does not modify the code already in the editor |

Further detail: [app guide](pdf-analyzer/README.md), [script-building guide](pdf-analyzer/README_SCRIPT_BUILDER.md), and [copyable scripts](pdf-analyzer/examples/).
