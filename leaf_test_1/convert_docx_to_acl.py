#!/usr/bin/env python3
"""Convert the source DOCX into an ACL-style LaTeX project.

The converter uses LibreOffice's HTML export to retain document order and
character formatting, while reading OMML directly from the DOCX so Word
equations remain editable LaTeX rather than raster images.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

from lxml import etree, html


HERE = Path(__file__).resolve().parent
DOCX = HERE / "CITS4012_full_v2_101703.docx"
OUTPUT = HERE / "CITS4012_full_v2_101703_acl.tex"
FIGURES = HERE / "figures"
SOFFICE = Path(
    "/Users/qiangwang/.cache/codex-runtimes/codex-primary-runtime/"
    "dependencies/bin/override/soffice"
)

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
NS = {"w": W_NS, "m": M_NS}


def math_text(text: str) -> str:
    replacements = {
        "α": r"\alpha ",
        "β": r"\beta ",
        "γ": r"\gamma ",
        "λ": r"\lambda ",
        "σ": r"\sigma ",
        "∈": r"\in ",
        "∩": r"\cap ",
        "∪": r"\cup ",
        "≤": r"\leq ",
        "≥": r"\geq ",
        "±": r"\pm ",
        "×": r"\times ",
        "⊙": r"\odot ",
        "∑": r"\sum ",
        "√": r"\sqrt{}",
        "−": "-",
        " ": r"\,",
        " ": r"\,",
        " ": r"\qquad ",
        "¯": r"\bar{}",
        "‾": r"\bar{}",
        "%": r"\%",
    }
    out = "".join(replacements.get(char, char) for char in text)
    out = out.replace("arg\u2006max", r"\operatorname*{arg\,max}")
    out = out.replace("softmax", r"\operatorname{softmax}")
    out = out.replace("maskedMean", r"\operatorname{maskedMean}")
    out = out.replace("maskedMax", r"\operatorname{maskedMax}")
    return out


def child(node: etree._Element, local_name: str) -> etree._Element | None:
    return node.find(f"{{{M_NS}}}{local_name}")


def omml_to_latex(node: etree._Element | None) -> str:
    if node is None:
        return ""
    tag = etree.QName(node).localname

    if tag in {"oMath", "oMathPara", "e", "num", "den", "sub", "sup", "deg"}:
        return "".join(omml_to_latex(part) for part in node)
    if tag == "r":
        return "".join(math_text(t.text or "") for t in node.findall(f"{{{M_NS}}}t"))
    if tag == "t":
        return math_text(node.text or "")
    if tag == "sSub":
        return f"{{{omml_to_latex(child(node, 'e'))}}}_{{{omml_to_latex(child(node, 'sub'))}}}"
    if tag == "sSup":
        return f"{{{omml_to_latex(child(node, 'e'))}}}^{{{omml_to_latex(child(node, 'sup'))}}}"
    if tag == "sSubSup":
        base = omml_to_latex(child(node, "e"))
        sub = omml_to_latex(child(node, "sub"))
        sup = omml_to_latex(child(node, "sup"))
        return f"{{{base}}}_{{{sub}}}^{{{sup}}}"
    if tag == "f":
        return rf"\frac{{{omml_to_latex(child(node, 'num'))}}}{{{omml_to_latex(child(node, 'den'))}}}"
    if tag == "rad":
        base = omml_to_latex(child(node, "e"))
        degree = omml_to_latex(child(node, "deg"))
        return rf"\sqrt[{degree}]{{{base}}}" if degree else rf"\sqrt{{{base}}}"
    if tag == "d":
        props = child(node, "dPr")
        begin, end = "(", ")"
        if props is not None:
            begin_node = child(props, "begChr")
            end_node = child(props, "endChr")
            if begin_node is not None:
                begin = begin_node.get(f"{{{M_NS}}}val", begin)
            if end_node is not None:
                end = end_node.get(f"{{{M_NS}}}val", end)
        body = "".join(omml_to_latex(e) for e in node.findall(f"{{{M_NS}}}e"))
        if begin == "|" and end == "|":
            return rf"\left\lvert {body} \right\rvert"
        return rf"\left{begin} {body} \right{end}"
    if tag == "acc":
        props = child(node, "accPr")
        mark = "¯"
        if props is not None:
            chr_node = child(props, "chr")
            if chr_node is not None:
                mark = chr_node.get(f"{{{M_NS}}}val", mark)
        body = omml_to_latex(child(node, "e"))
        return rf"\vec{{{body}}}" if mark in {"⃗", "→"} else rf"\bar{{{body}}}"
    if tag == "nary":
        props = child(node, "naryPr")
        operator = "∑"
        if props is not None:
            chr_node = child(props, "chr")
            if chr_node is not None:
                operator = chr_node.get(f"{{{M_NS}}}val", operator)
        op = {"∑": r"\sum", "∏": r"\prod", "∫": r"\int"}.get(operator, operator)
        sub = omml_to_latex(child(node, "sub"))
        sup = omml_to_latex(child(node, "sup"))
        base = omml_to_latex(child(node, "e"))
        limits = (f"_{{{sub}}}" if sub else "") + (f"^{{{sup}}}" if sup else "")
        return f"{op}{limits} {base}"

    # Property and control nodes carry formatting only.
    if tag.endswith("Pr") or tag in {"ctrlPr", "chr", "degHide"}:
        return ""
    return "".join(omml_to_latex(part) for part in node)


def load_equations() -> list[str]:
    with zipfile.ZipFile(DOCX) as archive:
        root = etree.fromstring(archive.read("word/document.xml"))
    equations = root.xpath(".//m:oMath", namespaces=NS)
    return [omml_to_latex(eq).strip() for eq in equations]


def tex_escape(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = text.replace("’", "'").replace("“", "``").replace("”", "''")
    text = text.replace("–", "--").replace("—", "---").replace("−", "-")
    table = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(table.get(char, char) for char in text)


class Converter:
    def __init__(self, equations: list[str]) -> None:
        self.equations = equations
        self.equation_index = 0
        self.figure_index = 0
        self.table_index = 0
        self.pending_figure: etree._Element | None = None
        self.pending_table_caption: str | None = None
        self.in_references = False

    def image_tex(self, element: etree._Element) -> str:
        name = element.get("name", "")
        if name.startswith("Object"):
            if self.equation_index >= len(self.equations):
                raise RuntimeError("HTML contains more equation images than the DOCX OMML stream")
            equation = self.equations[self.equation_index]
            self.equation_index += 1
            return f"${equation}$"
        return ""

    def _inline_tex(self, element: etree._Element) -> str:
        pieces: list[str] = []
        if element.text:
            pieces.append(tex_escape(element.text))
        for part in element:
            if not isinstance(part.tag, str):
                if part.tail:
                    pieces.append(tex_escape(part.tail))
                continue
            tag = part.tag.lower() if isinstance(part.tag, str) else ""
            if tag == "img":
                rendered = self.image_tex(part)
            elif tag == "br":
                rendered = r"\\"
            else:
                rendered = self._inline_tex(part)
                if tag in {"b", "strong"}:
                    rendered = rf"\textbf{{{rendered}}}"
                elif tag in {"i", "em"}:
                    rendered = rf"\textit{{{rendered}}}"
                elif tag == "sup":
                    rendered = rf"\textsuperscript{{{rendered}}}"
                elif tag == "sub":
                    rendered = rf"\textsubscript{{{rendered}}}"
                elif tag == "font" and (part.get("color") or "").lower() == "#ff0000":
                    rendered = rf"\textcolor{{red}}{{{rendered}}}"
            pieces.append(rendered)
            if part.tail:
                pieces.append(tex_escape(part.tail))
        return "".join(pieces)

    def inline_tex(self, element: etree._Element) -> str:
        joined = self._inline_tex(element)
        joined = re.sub(r"[ \t\r\n]+", " ", joined).strip()
        return joined

    @staticmethod
    def clean_heading(text: str) -> str:
        return re.sub(r"^\d+(?:\.\d+)+\s+", "", text).strip()

    @staticmethod
    def figure_images(element: etree._Element) -> list[etree._Element]:
        return [img for img in element.xpath(".//img") if not img.get("name", "").startswith("Object")]

    def figure_from(self, element: etree._Element, caption: str) -> str:
        images = self.figure_images(element)
        width = max(int(image.get("width", "0") or 0) for image in images)
        starred = width > 360
        env = "figure*" if starred else "figure"
        self.figure_index += 1
        lines = [f"\\begin{{{env}}}[t]", "  \\centering"]
        for index, image in enumerate(images):
            lines.append(f"  \\includegraphics[width=\\linewidth]{{figures/{image.get('data-target')}}}")
            if index + 1 < len(images):
                lines.append(r"  \\[-0.4em]")
        lines.extend([f"  \\caption{{{caption}}}", f"  \\label{{fig:{self.figure_index}}}", f"\\end{{{env}}}\n"])
        return "\n".join(lines)

    def unlabeled_figure_from(self, element: etree._Element) -> str:
        images = self.figure_images(element)
        lines = [r"\begin{center}"]
        for index, image in enumerate(images):
            lines.append(f"  \\includegraphics[width=\\columnwidth]{{figures/{image.get('data-target')}}}")
            if index + 1 < len(images):
                lines.append(r"  \\[-0.4em]")
        lines.append(r"\end{center}" + "\n")
        return "\n".join(lines)

    def table_from(self, table: etree._Element, caption: str) -> str:
        rows = table.xpath("./tr|./thead/tr|./tbody/tr")
        matrix = []
        for row in rows:
            cells = row.xpath("./th|./td")
            if cells:
                values = [self.inline_tex(cell) for cell in cells]
                matrix.append(["" if value.replace(r"\\", "").strip() == "" else value for value in values])
        if not matrix:
            return ""
        self.table_index += 1
        columns = max(len(row) for row in matrix)
        if self.table_index == 1:
            env, size, spec = "table", r"\scriptsize", r"@{}Xcc@{}"
            width = r"\columnwidth"
        elif self.table_index == 2:
            env, size, spec = "table*", r"\small", r"@{}lcc@{}"
            width = r"\textwidth"
        else:
            env, size, spec = "table*", r"\scriptsize", r"@{}p{0.24\textwidth}p{0.31\textwidth}ccc@{}"
            width = r"\textwidth"
        lines = [f"\\begin{{{env}}}[t]", "  \\centering", f"  {size}", f"  \\caption{{{caption}}}", f"  \\label{{tab:{self.table_index}}}"]
        if "X" in spec:
            lines.append(f"  \\begin{{tabularx}}{{{width}}}{{{spec}}}")
        else:
            lines.append(f"  \\begin{{tabular}}{{{spec}}}")
        lines.append("    \\toprule")
        for index, row in enumerate(matrix):
            padded = row + [""] * (columns - len(row))
            lines.append("    " + " & ".join(padded) + r" \\")
            if index == 0:
                lines.append("    \\midrule")
        lines.append("    \\bottomrule")
        lines.append("  \\end{tabularx}" if "X" in spec else "  \\end{tabular}")
        lines.append(f"\\end{{{env}}}\n")
        return "\n".join(lines)

    def convert(self, document: etree._Element) -> str:
        body = document.xpath("//body")[0]
        selected = body.xpath(".//h1|.//h2|.//h3|.//h4|.//p|.//table")
        selected = [node for node in selected if not node.xpath("ancestor::table") or node.tag == "table"]
        output: list[str] = []
        started = False

        for element in selected:
            tag = element.tag.lower()
            if self.in_references:
                continue
            if tag in {"h1", "h2", "h3", "h4"}:
                if self.pending_figure is not None:
                    output.append(self.unlabeled_figure_from(self.pending_figure))
                    self.pending_figure = None
                started = True
                heading = self.clean_heading(self.inline_tex(element))
                if heading == "References":
                    self.in_references = True
                    continue
                command = {"h1": "section", "h2": "subsection", "h3": "subsubsection", "h4": "paragraph"}[tag]
                output.append(rf"\{command}{{{heading}}}" + "\n")
                continue
            if not started:
                continue
            if tag == "table":
                caption = self.pending_table_caption or f"Table {self.table_index + 1}."
                caption = re.sub(r"^Table\s+\d+\.\s*", "", caption)
                output.append(self.table_from(element, caption))
                self.pending_table_caption = None
                continue

            non_math_images = [img for img in element.xpath(".//img") if not img.get("name", "").startswith("Object")]
            paragraph = self.inline_tex(element)
            if non_math_images:
                if self.pending_figure is not None:
                    output.append(self.unlabeled_figure_from(self.pending_figure))
                self.pending_figure = element
                continue
            if re.match(r"^Figure\s+\d+[a-z]?(?:--\d+[a-z]?)?\.\s*", paragraph) and self.pending_figure is not None:
                caption = re.sub(r"^Figure\s+\d+[a-z]?(?:--\d+[a-z]?)?\.\s*", "", paragraph)
                output.append(self.figure_from(self.pending_figure, caption))
                self.pending_figure = None
                continue
            if paragraph.startswith("Table "):
                self.pending_table_caption = paragraph
                continue
            if re.fullmatch(r"(?:\\\\\s*)+", paragraph):
                continue
            if paragraph:
                output.append(paragraph + "\n")

        if self.pending_figure is not None:
            output.append(self.unlabeled_figure_from(self.pending_figure))
            self.pending_figure = None
        if self.equation_index != len(self.equations):
            raise RuntimeError(
                f"Equation stream mismatch: used {self.equation_index} of {len(self.equations)} OMML equations"
            )
        return "\n".join(output)


def rewrite_citations(text: str) -> str:
    text = text.replace(
        "(Sanh et al., 2019; Liu et al., 2019)",
        r"\citep{sanh2019distilbert,liu2019roberta}",
    )
    replacements = {
        "(Bisk et al., 2020)": r"\citep{bisk2020piqa}",
        "(Hochreiter and Schmidhuber, 1997)": r"\citep{hochreiter1997long}",
        "Mueller and Thyagarajan, 2016": r"\citet{mueller2016siamese}",
        "(Vaswani et al., 2017)": r"\citep{vaswani2017attention}",
        "(Luong et al., 2015)": r"\citep{luong2015effective}",
        "Luong et al., 2015": r"\citet{luong2015effective}",
        "(Yang et al., 2016)": r"\citep{yang2016hierarchical}",
        "Yang et al., 2016": r"\citet{yang2016hierarchical}",
        "Chen et al. (2017)": r"\citet{chen2017esim}",
        "(Conneau et al., 2017)": r"\citep{conneau2017infersent}",
        "Conneau et al., 2017": r"\citet{conneau2017infersent}",
        "(Kingma and Ba, 2015)": r"\citep{kingma2015adam}",
        "(Sanh et al., 2019)": r"\citep{sanh2019distilbert}",
        "(Mosbach et al., 2021)": r"\citep{mosbach2021stability}",
        "(Liu et al., 2019)": r"\citep{liu2019roberta}",
        "(Dufter et al., 2020)": r"\citep{dufter2020increasing}",
        "Dufter et al. (2020)": r"\citet{dufter2020increasing}",
        "(Seo et al., 2017)": r"\citep{seo2017bidaf}",
        "(Bachlechner et al., 2021)": r"\citep{bachlechner2021rezero}",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    text = text.replace("Qwen/Qwen2.5-3B-Instruct", r"Qwen/Qwen2.5-3B-Instruct \citep{qwen2024}")
    return text


def export_html() -> tuple[Path, tempfile.TemporaryDirectory[str]]:
    temp = tempfile.TemporaryDirectory(prefix="cits4012_acl_")
    subprocess.run(
        [str(SOFFICE), "--headless", "--convert-to", "html", "--outdir", temp.name, str(DOCX)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    html_path = Path(temp.name) / f"{DOCX.stem}.html"
    if not html_path.exists():
        raise RuntimeError("LibreOffice did not produce the expected HTML export")
    return html_path, temp


def copy_figures(document: etree._Element, source_dir: Path) -> None:
    FIGURES.mkdir(exist_ok=True)
    for old in FIGURES.glob("*.png"):
        old.unlink()
    images = document.xpath('//img[not(starts-with(@name,"Object"))]')
    for index, image in enumerate(images, start=1):
        source = source_dir / image.get("src")
        target_name = f"figure_{index}.png"
        shutil.copy2(source, FIGURES / target_name)
        image.set("data-target", target_name)


def main() -> None:
    html_path, temp = export_html()
    try:
        document = html.fromstring(html_path.read_bytes())
        copy_figures(document, html_path.parent)
        body = Converter(load_equations()).convert(document)
    finally:
        temp.cleanup()

    body = rewrite_citations(body)
    for source, target in {
        "√D": r"$\sqrt{D}$",
        "β": r"$\beta$",
        "γ": r"$\gamma$",
        "λ": r"$\lambda$",
        "±": r"$\pm$",
    }.items():
        body = body.replace(source, target)
    body = re.sub(r"\$ ([,.;:])", r"$\1", body)
    preamble = r"""% Converted from CITS4012_full_v2_101703.docx.
% ACL style files: https://github.com/acl-org/acl-style-files
\documentclass[11pt]{article}
\usepackage[final]{acl}
\usepackage{times}
\usepackage{latexsym}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{tabularx}
\usepackage{array}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{microtype}
\usepackage[T1]{fontenc}
\hypersetup{pdftitle={CITS4012 PIQA Report},pdfauthor={Group XX}}

\title{CITS4012 PIQA Report}
\author{Group XX}

\begin{document}
\maketitle

"""
    ending = r"""
\bibliography{references}
\end{document}
"""
    OUTPUT.write_text(preamble + body + ending, encoding="utf-8")
    shutil.copy2("/private/tmp/acl.sty", HERE / "acl.sty")
    shutil.copy2("/private/tmp/acl_natbib.bst", HERE / "acl_natbib.bst")
    shutil.copy2("/private/tmp/acl_latex.tex", HERE / "acl_latex.tex")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
