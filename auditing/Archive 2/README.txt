CITS4012 Group Project -- PIQA
LaTeX source package
==============================================================

PAGE COUNT  (rule: content <= 6 pages, figures and tables
included; Team Contributions and References excluded)

    pages 1-6 .......... content                     = 6 pages  OK
    page  7 ............ Team Contributions + References (excluded)

    Built with the REAL acl.sty (A4, 2.5cm margins, 0.6cm column
    separation), so this is the page count Overleaf will give.

    The margin is about one line. Anything added needs an equal
    cut; the Limitations paragraph is what sits at the very end.

--------------------------------------------------------------
BEFORE SUBMITTING -- three things
--------------------------------------------------------------
1. ALREADY DONE -- main.tex now uses the real acl.sty, which is
   in this folder. On Overleaf you still need acl_natbib.bst
   from https://github.com/acl-org/acl-style-files (it is the
   bibliography style acl.sty asks for; it is not included here).
   Compile with pdfLaTeX.

2. Rename to CITS4012_15.pdf and CITS4012_15.ipynb
   (title and \author{Group 15} are already set)

3. CHECK THE B3 PROMPT AGAINST THE NOTEBOOK.
   Section 3.4 now prints the prompt as
       Goal: {g}, Solution: {s_k}
   with a comma. If the notebook actually used a newline
   (\n), the report and the code disagree, and the brief
   deducts marks for exactly that. Either change the
   notebook to match, or put the newline back in main.tex.

--------------------------------------------------------------
STILL NEEDS RAY
--------------------------------------------------------------
Figures 9 and 10 (attention heat maps) have token labels that
render at about 2.2pt in a single column. Hard to read in
print, and the assignment asks for visualisations that "can be
interpreted".

Scaling cannot fix it: the text is ~1% of the image width, so
even at full column width it only reaches 2.2pt. They need
regenerating with the font roughly 3x larger relative to the
figure -- set a small figsize (about 3.2 x 2.0 in) and let
matplotlib size the text for it, instead of saving a 28in-wide
figure and shrinking it. Fewer tokens per panel also helps.
Drop the new files in with the same names; no .tex change.

--------------------------------------------------------------
FLOATS, AND WHAT EACH COSTS IF YOU NEED TO CUT
--------------------------------------------------------------
                                        required by    cost if
                                        the brief?     removed
  Fig 1  Task characteristics              no          ~0.15 pg
  Fig 2  Model architecture (full width)   YES         --
  Fig 3  Hyperparameter sweep (full width) no          ~0.30 pg
  Fig 4  Baseline comparison               no          ~0.15 pg
  Fig 5  Ablation plot                     no          ~0.18 pg
  Fig 6  Temperature heat maps             no          ~0.15 pg
  Fig 7  Full model, correct prediction    YES         --
  Fig 8  Ablation error                    YES         --
  Tab 1  Dataset statistics                YES(desc)   --
  Tab 2  Validation ablations              YES         --
  Tab 3  Accuracy on both splits           YES         --

  "YES" = the assignment names it: an architecture diagram,
  ablation results, overall comparison, and attention
  visualisations of BOTH a successful and a failed prediction.

  The cheapest page to recover is Fig 3 + Fig 5 (~0.5 pg),
  since Table 2 already carries every ablation row and the
  hyperparameter results are all stated in Section 3.3.

--------------------------------------------------------------
removed_figures/
--------------------------------------------------------------
  fig3_convergence.png   epoch budget   -> text, Section 3.2
  fig7b_temp_sol2.png    solution 2     -> you asked to cut it

--------------------------------------------------------------
CHECKS ON THIS BUILD
--------------------------------------------------------------
  0 undefined references      0 undefined citations
  0 overfull boxes > 15pt     all 11 floats cited in text
  all 16 bibliography entries cited
