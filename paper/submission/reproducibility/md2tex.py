#!/usr/bin/env python3
"""Convert the PAIR-SV manuscript markdown to LaTeX for tectonic.

Handles only what this document actually contains: headings, bold/italic,
inline code, pipe tables, image+caption pairs, bullet lists, horizontal
rules and links. Tables become longtable so they can break across pages.
"""
import re
import sys
from pathlib import Path

SRC = Path(sys.argv[1])
DST = Path(sys.argv[2])

UNI = {
    "§": r"\S{}", "±": r"$\pm$", "≤": r"$\le$", "≥": r"$\ge$", "≈": r"$\approx$",
    "×": r"$\times$", "Δ": r"$\Delta$", "−": "-", "—": "---", "–": "--",
    "⁻": r"$^-$", "⁴": r"$^4$", "’": "'", "‘": "'", "“": "``", "”": "''",
    "…": r"\ldots{}", "ä": r'\"a', "ö": r'\"o', "ü": r'\"u', "é": r"\'e", "í": r"\'i", "ó": r"\'o", "→": r"$\rightarrow$", "≠": r"$\neq$", "\u00a0": "~",
}
ESC = {"&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_",
       "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}


def brk(s: str, every: int = 10) -> str:
    """Insert breakpoints in long unbroken runs so hashes/paths can wrap."""
    out, run = [], 0
    for ch in s:
        out.append(ch)
        if ch == "/":
            out.append(r"\allowbreak{}")
            run = 0
            continue
        run = run + 1 if ch.isalnum() else 0
        if run >= every:
            out.append(r"\allowbreak{}")
            run = 0
    return "".join(out)


def esc(s: str) -> str:
    """Escape LaTeX specials, then map unicode. Backslash first."""
    s = s.replace("\\", r"\textbackslash{}")
    for k, v in ESC.items():
        s = s.replace(k, v)
    for k, v in UNI.items():
        s = s.replace(k, v)
    return s


def inline(s: str) -> str:
    """Inline markup -> LaTeX. Code spans are escaped, then protected."""
    out, i, parts = "", 0, []
    for m in re.finditer(r"`([^`]+)`", s):
        parts.append((m.start(), m.end(), m.group(1)))
    if parts:
        buf, last = "", 0
        for a, b, code in parts:
            buf += esc(s[last:a]) + r"\texttt{" + brk(esc(code)) + "}"
            last = b
        buf += esc(s[last:])
        s = buf
    else:
        s = esc(s)
    # links: [text](url) -- markdown brackets survived escaping
    s = re.sub(r"\[([^\]]+)\]\((https?://[^\)]+)\)", r"\\href{\2}{\1}", s)
    s = re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", s)
    s = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\\emph{\1}", s)
    return s


def table(rows):
    header, body = rows[0], rows[2:]
    n = len(header)
    # width heuristic: give wide text columns more room
    # A single very long cell must not starve the other columns, and no
    # column may be narrower than its longest unbreakable word.
    CPL = 139.0  # characters per line at footnotesize on this page geometry
    floors, desired = [], []
    for c in range(n):
        cells = [r[c] for r in rows if len(r) > c]
        longest_word = max((max((len(w) for w in cell.split()), default=0)
                            for cell in cells), default=4)
        floors.append(min(longest_word, 26) / CPL)
        desired.append(max(max((len(x) for x in cells), default=4), 4) ** 0.5)
    if sum(floors) > 0.85:                      # pathological table: scale floors down
        k = 0.85 / sum(floors)
        floors = [f * k for f in floors]
    slack = 1.0 - sum(floors)
    dtot = sum(desired)
    fracs = [f + slack * d / dtot for f, d in zip(floors, desired)]
    spec = "".join(
        ">{\\raggedright\\arraybackslash}p{\\dimexpr %.4f\\linewidth-2\\tabcolsep\\relax}" % w
        for w in fracs)
    out = [r"\begingroup\footnotesize", r"\setlength{\tabcolsep}{3pt}",
           r"\begin{longtable}{%s}" % spec, r"\hline"]
    out.append(" & ".join(r"\textbf{%s}" % inline(h) for h in header) + r" \\ \hline")
    out.append(r"\endfirsthead \hline")
    out.append(" & ".join(r"\textbf{%s}" % inline(h) for h in header) + r" \\ \hline")
    out.append(r"\endhead")
    for r in body:
        r = (r + [""] * n)[:n]
        out.append(" & ".join(brk(inline(c), 14) for c in r) + r" \\")
    out += [r"\hline", r"\end{longtable}", r"\endgroup", ""]
    return out


def main():
    lines = SRC.read_text().split("\n")
    body, i, n = [], 0, len(lines)
    in_list = False

    def close_list():
        nonlocal in_list
        if in_list:
            body.append(r"\end{itemize}")
            in_list = False

    title = None
    while i < n:
        L = lines[i]
        s = L.strip()

        if s.startswith("# ") and title is None:
            title = inline(s[2:]); i += 1; continue

        # image followed by a **Figure N.** caption paragraph
        m = re.match(r"!\[[^\]]*\]\((figures/[^\)]+)\)", s)
        if m:
            close_list()
            path = m.group(1)
            cap = ""
            j = i + 1
            while j < n and not lines[j].strip():
                j += 1
            if j < n and lines[j].strip().startswith("**Figure"):
                cap = inline(lines[j].strip()); j += 1
            body += [r"\begin{figure}[H]", r"\centering",
                     r"\includegraphics[width=\linewidth,height=0.42\textheight,keepaspectratio]{%s}" % path,
                     r"\caption*{%s}" % cap, r"\end{figure}", ""]
            i = j; continue

        if s.startswith("### "):
            close_list(); body += [r"\subsection*{%s}" % inline(s[4:]), ""]; i += 1; continue
        if s.startswith("## "):
            close_list(); body += [r"\section*{%s}" % inline(s[3:]), ""]; i += 1; continue
        if s.startswith("# "):
            close_list(); body += [r"\section*{%s}" % inline(s[2:]), ""]; i += 1; continue

        if s in ("---", "***"):
            close_list(); body += [r"\vspace{0.6em}\hrule\vspace{0.6em}", ""]; i += 1; continue

        if s.startswith("|") and i + 1 < n and re.match(r"^\|[\s\-:|]+\|$", lines[i + 1].strip()):
            close_list()
            rows = []
            while i < n and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                rows.append(cells); i += 1
            body += table(rows); continue

        if s.startswith("- "):
            if not in_list:
                body.append(r"\begin{itemize}\setlength{\itemsep}{2pt}"); in_list = True
            body.append(r"\item " + inline(s[2:])); i += 1; continue

        if not s:
            close_list(); body.append(""); i += 1; continue

        close_list(); body.append(inline(s)); i += 1

    close_list()

    pre = r"""\documentclass[10pt]{article}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage[a4paper,margin=2.2cm]{geometry}
\usepackage{longtable,array,graphicx,hyperref,caption,microtype}
\usepackage{float}  %% [H] keeps figures in place; longtable is not float-aware
\usepackage[table]{xcolor}
\captionsetup{font=small,justification=raggedright,singlelinecheck=false}
\setlength{\parindent}{0pt}\setlength{\parskip}{0.55em}
\hypersetup{colorlinks=true,linkcolor=black,urlcolor=blue!60!black}
\graphicspath{{./}}
\sloppy
\emergencystretch=3em
\hbadness=10000
\raggedbottom
\vbadness=10000
\title{\textbf{%s}}
\date{}
\begin{document}
\maketitle
""" % (title or "Manuscript")
    DST.write_text(pre + "\n".join(body) + "\n\\end{document}\n")
    print(f"wrote {DST} ({len(body)} lines)")


main()
