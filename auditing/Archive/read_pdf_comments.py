#!/usr/bin/env python3
"""
Read the comments out of an annotated PDF and show, for each one,
the text it is attached to.

    python3 -I read_pdf_comments.py annotated.pdf

Needs pypdf and poppler's pdftotext, both already in the sandbox.
"""
import re
import subprocess
import sys

from pypdf import PdfReader

SKIP = {"/Link", "/Popup"}


def word_boxes(path):
    """Per page: (width, height, [(xmin, ymin, xmax, ymax, word), ...])."""
    xml = subprocess.run(
        ["pdftotext", "-bbox", path, "-"], capture_output=True, text=True
    ).stdout
    pages = []
    for pm in re.finditer(
        r'<page width="([\d.]+)" height="([\d.]+)">(.*?)</page>', xml, re.S
    ):
        words = [
            (
                float(m.group(1)),
                float(m.group(2)),
                float(m.group(3)),
                float(m.group(4)),
                m.group(5),
            )
            for m in re.finditer(
                r'<word xMin="([\d.]+)" yMin="([\d.]+)" '
                r'xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</word>',
                pm.group(3),
            )
        ]
        pages.append((float(pm.group(1)), float(pm.group(2)), words))
    return pages


def anchored_text(annot, page, grid, pad=2.0):
    """The words sitting under an annotation's rectangle."""
    box = annot.get("/Rect")
    if not box:
        return ""
    rect = [float(v) for v in box]
    page_h = float(page.mediabox.height)
    page_w = float(page.mediabox.width)
    width, height, words = grid
    sx, sy = width / page_w, height / page_h

    x0, x1 = min(rect[0], rect[2]) * sx, max(rect[0], rect[2]) * sx
    # PDF is bottom-left origin, pdftotext -bbox is top-left
    t0 = (page_h - max(rect[1], rect[3])) * sy
    t1 = (page_h - min(rect[1], rect[3])) * sy

    hits = [
        w[4]
        for w in words
        if w[0] < x1 and w[2] > x0 and w[1] < t1 + pad and w[3] > t0 - pad
    ]
    return " ".join(hits)


def main(path):
    reader = PdfReader(path)
    grids = word_boxes(path)
    found = 0

    for i, page in enumerate(reader.pages):
        for ref in page.get("/Annots") or []:
            annot = ref.get_object()
            subtype = str(annot.get("/Subtype"))
            if subtype in SKIP:
                continue

            comment = annot.get("/Contents")
            comment = str(comment).strip() if comment else ""
            author = annot.get("/T")
            context = anchored_text(annot, page, grids[i]) if i < len(grids) else ""

            # A FreeText box paints its own words onto the page, so the
            # anchor just echoes the comment -- not useful as context.
            if subtype == "/FreeText" and context.strip() == comment.strip():
                context = "(free-text box; no underlying text)"

            found += 1
            print(f"\n[{found}] page {i + 1}   {subtype.lstrip('/')}"
                  + (f"   by {author}" if author else ""))
            if comment:
                print(f"     comment : {comment}")
            else:
                print("     comment : (none -- mark only, no note attached)")
            if context:
                print(f"     attached to: {context[:300]}")

    print(f"\n{found} comment(s) found.")
    if not found:
        print(
            "Nothing extractable. The PDF may have been flattened, or the\n"
            "annotations were drawn as images rather than saved as PDF\n"
            "annotations. Re-export from the annotating app, or paste the\n"
            "comments as text instead."
        )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python3 -I read_pdf_comments.py <annotated.pdf>")
    main(sys.argv[1])
