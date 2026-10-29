# PAIR-SV Train15 publication-package final audit

## Build evidence

- Tectonic: `Tectonic 0.16.9`.
- Main command: `tectonic paper/PAIR_SV_Train15_article_draft.tex --outdir paper/build --keep-logs --keep-intermediates`.
- Supplement command: `tectonic paper/PAIR_SV_Train15_supplementary.tex --outdir paper/build --keep-logs --keep-intermediates`.
- Main compile exit code: 0. Supplement compile exit code: 0.
- Main render command: `pdftoppm -png -r 170 paper/PAIR_SV_Train15_article_draft.pdf paper/rendered_pages/page`.
- Supplement render command: `pdftoppm -png -r 160 paper/PAIR_SV_Train15_supplementary.pdf paper/rendered_supplementary_pages/page`.
- Main PDF SHA-256: `d35f0efe2ef68d7d329dee4dc09eb58e341b87f2474c4058c86c95a9a37ed453`.
- Supplement PDF SHA-256: `976436f19b61349cba4c46bad1730f4e4354b3592d590721091293e72ef9f288`.

## Acceptance checks

- `pdfinfo` reports **6 physical pages** for the main PDF. References begin on page 6, so the main manuscript occupies **5 pages before references**.
- `pdfinfo` reports **3 pages** for the supplementary PDF.
- The main paper embeds **5 original PAIR-SV figures** and **4 rendered main-paper tables**.
- The PDF renders **11 bibliography entries**. `references.bib` mirrors the same verified bibliography.
- Unresolved citation/reference warning count: **0**. There are no `??` references or unresolved citations.
- Raw Markdown marker scan: **0** in LaTeX sources; page-PNG visual inspection confirms no literal heading markers, emphasis markers, backticks, or `See references.bib` placeholder in either PDF.
- Main-table layout raised two compact-table overfull-box diagnostics and the supplement raised one 5.5-pt checksum-line diagnostic. The rendered PNG audit found **no visible clipping, overlap, margin overflow or truncated text**.
- Figure 2 was redrawn as four lanes with a single aligned fusion/output column. All box labels remain inside their boxes at rendered scale; source labels are at least 8.05 pt before the near-full-width placement.
- Figure 3 is in source before Discussion/Conclusion. Discussion and Conclusion are continuous in normal column flow on page 5; neither is separated by a Figure 3 float or orphaned conclusion fragment.
- Figure 5 contains only branch names, axis labels and numeric changes. Its methodological warning is in the caption and text, not inside the plot.
- No internal-test metrics, predictions or people are present. Mentions of the internal-test cohort only document the planned 40/5/5 boundary and its non-use.

## Reference verification

All 11 bibliography entries were checked against a primary publisher page, PubMed record, official proceedings entry, or official resource record before this build. The corrected DeepVariant DOI is `10.1038/nbt.4235`; the PanGenie title is *Pangenome-based genome inference allows efficient and accurate genotyping across a wide spectrum of variant classes*. DELLY, LUMPY, SVHunter and the Mahmoud et al. review were added with verified DOI metadata. The verified title is **SVHunter** (not “HunterSV”); it is accurately described as related long-read CNN/Transformer work rather than a direct benchmark.

## Artifact provenance and numerical consistency

- Main metrics source: `reports/pairsv_train15_main_metrics.csv`, SHA-256 `d3a8294b57539c7612cadfacfb568cedfe9829c3ad0be4c5d79a303e8e9d9cc8`.
- Bootstrap source: `reports/pairsv_train15_bootstrap.csv`, SHA-256 `8963c9699aab5e785730d21eaac80e3b3e671f1393304e9f87c8454920d70ec2`.
- Ablation source: `reports/pairsv_train15_ablations.csv`, SHA-256 `151cbb7932ceb1cb6ebeafeb46e71c3dbf16b298649fe62acd98873e0c479013`.
- Subgroup source: `reports/pairsv_train15_subgroup_metrics.csv`, SHA-256 `6341730e9c997398e3faab6aefe39798cfab81b231dc1a16962466d4f02e64e0`.
- Direct display-precision checks against those authoritative CSVs passed: M0/M2/M4 loss, threshold, precision, recall, F1, ROC-AUC, PR-AUC, MCC, confusion matrices, parameter counts and training times; the three bootstrap F1 differences and intervals; zero/shuffle interventions; and subgroup/per-person values in the supplement.
- The LaTeX manuscript, companion Markdown, Russian summary and PDFs therefore agree on the headline controlled values: M0 F1 0.7991, M2 F1 0.7980 and M4 F1 0.8062.

## Page-level visual inspection

### Main manuscript

| Page | Visual inspection result |
|---|---|
| 1 | Title, structured abstract, introduction and expanded related work render cleanly in two columns. |
| 2 | Same-site design, methods and results opening are readable; no overlap or raw Markdown. |
| 3 | Dataset/QC table, repaired four-lane architecture, variant and bootstrap tables are legible; Figure 2 labels and arrows do not overlap. |
| 4 | Controlled-results table and literal five-category pileup composite render with readable breakpoint markers; Figure 3 precedes later discussion. |
| 5 | Controlled metrics/bootstrap and compact Figure 5 render cleanly; the plot has no embedded methodological paragraph. Discussion and Conclusion follow continuously in normal column flow, without a Figure 3 interruption. |
| 6 | Data/code statement and all 11 rendered references are legible; no unresolved references. |

### Supplement

| Page | Visual inspection result |
|---|---|
| 1 | Strict label rules and complete 17-feature table are readable. |
| 2 | Extraction schema, QC, fixed training protocol and subgroup table are complete and unclipped. |
| 3 | Per-person table, zero/shuffle interventions, bootstrap limitation and reproducibility hashes are rendered as actual material, not a placeholder. |

## Remaining scientific limitations

This is a one-seed, 15-person-training intermediate validation result. It has validation-selected thresholds, silver labels, pairability filtering, candidate re-use across people and row-level rather than candidate-cluster bootstrap. It is selected-candidate deletion classification, not genome-wide discovery. Final claims still require full 40-person training, three seeds, candidate-cluster uncertainty and exactly one final evaluation of the untouched five-person internal-test cohort.
