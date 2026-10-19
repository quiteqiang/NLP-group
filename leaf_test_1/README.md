# CITS4012 ACL LaTeX conversion

The Word report has been converted to an ACL-style LaTeX project using the
official files from <https://github.com/acl-org/acl-style-files>.

## Main files

- `CITS4012_full_v2_101703_acl.tex` is the editable LaTeX source.
- `CITS4012_full_v2_101703_acl.pdf` is the compiled PDF.
- `references.bib` contains the report bibliography.
- `figures/` contains the ten images extracted from the DOCX.
- `acl.sty` and `acl_natbib.bst` are the official ACL style files.
- `convert_docx_to_acl.py` reproduces the DOCX-to-LaTeX conversion.

The source DOCX did not contain a title page or abstract. The conversion adds
the conservative placeholders `CITS4012 PIQA Report` and `Group XX`; replace
them before submission. Visible red revisions and the bold `[TO DO: RAY ...]`
paragraph are preserved from the DOCX rather than silently removed.

## Build

Run these commands inside this folder:

```bash
pdflatex -interaction=nonstopmode -halt-on-error CITS4012_full_v2_101703_acl.tex
bibtex CITS4012_full_v2_101703_acl
pdflatex -interaction=nonstopmode -halt-on-error CITS4012_full_v2_101703_acl.tex
pdflatex -interaction=nonstopmode -halt-on-error CITS4012_full_v2_101703_acl.tex
```
