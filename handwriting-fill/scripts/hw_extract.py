#!/usr/bin/env python3
"""Pull pen strokes out of a PDF exported from a note-taking app (GoodNotes etc.).

Such apps export handwriting as vector paths (round-capped stroked lines), so the
exact pen movement can be recovered. Output: JSON list of {"pts": [[x,y],...], "w": width}
in PDF points, origin at the top-left of the page.

usage: hw_extract.py sample.pdf strokes.json [--page N]
"""
import re, json, sys, subprocess, tempfile, os, collections

def extract(pdf, page=1):
    with tempfile.TemporaryDirectory() as td:
        svg = os.path.join(td, "p.svg")
        subprocess.run(["pdftocairo", "-svg", "-f", str(page), "-l", str(page), pdf, svg], check=True)
        s = open(svg, encoding="utf-8").read()
    strokes = []
    for m in re.finditer(r'<path [^>]*>', s):
        tag = m.group(0)
        if 'fill="none"' not in tag or 'stroke-linecap="round"' not in tag:
            continue
        sw = re.search(r'stroke-width="([\d.]+)"', tag)
        dm = re.search(r' d="([^"]*)"', tag)
        if not sw or not dm:
            continue
        tm = re.search(r'transform="matrix\(([^)]*)\)"', tag)
        a, b, c, d, e, f = [float(x) for x in tm.group(1).split(',')] if tm else (1, 0, 0, 1, 0, 0)
        T = lambda x, y: (a * x + c * y + e, b * x + d * y + f)
        toks = re.findall(r'[MLCZ]|-?\d+\.?\d*(?:e-?\d+)?', dm.group(1))
        pts, i, cur = [], 0, None
        while i < len(toks):
            t = toks[i]
            if t in 'ML':
                cur = (float(toks[i + 1]), float(toks[i + 2])); pts.append(T(*cur)); i += 3
            elif t == 'C':
                x1, y1, x2, y2, x3, y3 = [float(v) for v in toks[i + 1:i + 7]]
                x0, y0 = cur
                for k in range(1, 5):
                    u = k / 4; w = 1 - u
                    pts.append(T(w**3 * x0 + 3 * w * w * u * x1 + 3 * w * u * u * x2 + u**3 * x3,
                                 w**3 * y0 + 3 * w * w * u * y1 + 3 * w * u * u * y2 + u**3 * y3))
                cur = (x3, y3); i += 7
            elif t == 'Z':
                i += 1
            else:  # implicit lineto
                cur = (float(toks[i]), float(toks[i + 1])); pts.append(T(*cur)); i += 2
        if pts:
            strokes.append({"pts": [[round(x, 3), round(y, 3)] for x, y in pts],
                            "w": round(float(sw.group(1)) * abs(a * d - b * c) ** 0.5, 3)})
    return strokes

if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    page = int(sys.argv[sys.argv.index("--page") + 1]) if "--page" in sys.argv else 1
    st = extract(sys.argv[1], page)
    json.dump(st, open(sys.argv[2], "w"))
    if not st:
        sys.exit("No pen strokes found. The PDF probably holds the handwriting as an image "
                 "(a photo or scan); this tool needs a vector export from the note app.")
    xs = [p[0] for s in st for p in s["pts"]]; ys = [p[1] for s in st for p in s["pts"]]
    widths = collections.Counter(s["w"] for s in st)
    print("strokes: %d   pen widths: %s" % (len(st), dict(widths)))
    print("bbox: x %.0f-%.0f  y %.0f-%.0f (pt, from top-left)" % (min(xs), max(xs), min(ys), max(ys)))
