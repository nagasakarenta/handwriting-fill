#!/usr/bin/env python3
"""Cut a page of pen strokes into single characters and add them to a glyph bank.

The writer wrote known characters in known order, row by row. Strokes are grouped into
rows (by vertical position), each row into characters (strokes that overlap horizontally
belong together), and the characters are labelled in reading order.

usage:
  hw_segment.py strokes.json --rows "abcdefghij" "klmnopqrst" ... --bank bank.json
                [--debug debug.pdf] [--bands "0-100,100-150"] [--row-gap 12]
                [--gap 1.0] [--region x0,y0,x1,y1] [--max-width 100] [--dry-run]

  --rows       one string per row, top to bottom; characters in the order written.
               Use ? for a blob to skip (a stray mark, an illegible attempt).
  --bands      explicit row y-ranges in pt, when automatic row detection gets it wrong.
  --row-gap    automatic rows: a vertical jump larger than this starts a new row.
  --gap        strokes closer than this (pt) horizontally are the same character.
               Negative = they must overlap by that much (use for tightly written digits).
  --region     only use strokes whose centre lies in this box.
  --max-width  ignore strokes wider than this (underlines, table rules).
  --debug      write a sheet with every blob coloured and numbered; convert it to PNG
               (pdftoppm -r 80 -png) and LOOK at it before trusting the labels.
The bank is appended to, so several samples can be merged (more variants per character
look more natural).
"""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hw_pdf import write_pdf

XH_SET = "acemnorsuvwxz"; CAP_SET = "ABCDEFHIKLMNPRSTUVWXYZ"; DIG_SET = "0123568"

def med(v):
    v = sorted(v); return v[len(v) // 2]

def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default

def main():
    if len(sys.argv) < 2 or "--rows" not in sys.argv:
        sys.exit(__doc__)
    S = json.load(open(sys.argv[1]))
    i = sys.argv.index("--rows") + 1; rows = []
    while i < len(sys.argv) and not sys.argv[i].startswith("--"):
        rows.append(sys.argv[i].replace(" ", "")); i += 1
    gap = float(arg("--gap", "1.0")); row_gap = float(arg("--row-gap", "12"))
    maxw = float(arg("--max-width", "1e9"))
    region = [float(v) for v in arg("--region").split(",")] if arg("--region") else None
    B = []
    for k, s in enumerate(S):
        xs = [p[0] for p in s["pts"]]; ys = [p[1] for p in s["pts"]]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        if x1 - x0 > maxw: continue
        if region and not (region[0] <= (x0 + x1) / 2 <= region[2] and region[1] <= (y0 + y1) / 2 <= region[3]): continue
        B.append({"x0": x0, "x1": x1, "y0": y0, "y1": y1, "cy": (y0 + y1) / 2, "k": k})
    if not B: sys.exit("no strokes left after filtering")
    # --- rows ---
    if arg("--bands"):
        bands = [tuple(float(v) for v in b.split("-")) for b in arg("--bands").split(",")]
        groups = [[b for b in B if lo <= b["cy"] < hi] for lo, hi in bands]
    else:
        B.sort(key=lambda b: b["cy"]); groups = [[B[0]]]
        for b in B[1:]:
            if b["cy"] - groups[-1][-1]["cy"] > row_gap: groups.append([])
            groups[-1].append(b)
    print("rows found: %d (expected %d)" % (len(groups), len(rows)))
    for gi, g in enumerate(groups):
        print("  row %d: y %.0f-%.0f, %d strokes" % (gi, min(b["y0"] for b in g), max(b["y1"] for b in g), len(g)) if g else "  row %d: empty" % gi)
    # --- characters ---
    ok = len(groups) == len(rows); clusters = []
    for gi, g in enumerate(groups):
        g.sort(key=lambda b: b["x0"]); cl = []
        for b in g:
            if cl and b["x0"] < cl[-1]["x1"] + gap:
                cl[-1]["x1"] = max(cl[-1]["x1"], b["x1"]); cl[-1]["ids"].append(b["k"])
            else:
                cl.append({"x0": b["x0"], "x1": b["x1"], "ids": [b["k"]]})
        want = rows[gi] if gi < len(rows) else ""
        flag = "" if len(cl) == len(want) else "   <-- MISMATCH"
        if flag: ok = False
        print("  row %d: %d blobs, labels given: %d %s" % (gi, len(cl), len(want), flag))
        for ci, c in enumerate(cl):
            c["row"] = gi; c["idx"] = ci; c["label"] = want[ci] if len(cl) == len(want) else None
            clusters.append(c)
    # --- debug sheet ---
    if arg("--debug"):
        cols = [(0.8, 0, 0), (0, 0.35, 0.8), (0, 0.5, 0), (0.8, 0.4, 0), (0.55, 0, 0.6), (0, 0.5, 0.5)]
        X0 = min(b["x0"] for b in B) - 15; Y0 = min(b["y0"] for b in B) - 20; Z = 2.5
        W = (max(b["x1"] for b in B) - X0 + 15) * Z; H = (max(b["y1"] for b in B) - Y0 + 15) * Z
        st, lb = [], []
        for c in clusters:
            ys = []
            for k in c["ids"]:
                pts = [((p[0] - X0) * Z, (p[1] - Y0) * Z) for p in S[k]["pts"]]
                st.append((pts, cols[c["idx"] % 6], 1.8)); ys += [p[1] for p in pts]
            lb.append(((c["x0"] - X0) * Z, min(ys) - 4, "%d%s" % (c["idx"], (":" + c["label"]) if c["label"] else ""), 8))
        write_pdf(arg("--debug"), W, H, st, lb)
        print("debug sheet:", arg("--debug"))
    if not ok:
        sys.exit("Row or blob counts do not match the labels. Look at the debug sheet, then fix --rows "
                 "(use ? to skip a blob), --gap, --bands or --region. Nothing was added to the bank.")
    if "--dry-run" in sys.argv:
        print("dry run: labels match, nothing written"); return
    # --- reference sizes of this sample (so samples written at different sizes can be mixed) ---
    H = lambda ch_set: [max(S[k]["pts"][j][1] for k in c["ids"] for j in range(len(S[k]["pts"]))) -
                        min(S[k]["pts"][j][1] for k in c["ids"] for j in range(len(S[k]["pts"])))
                        for c in clusters if c["label"] and c["label"] in ch_set]
    caps, digs, xhs = H(CAP_SET), H(DIG_SET), H(XH_SET)
    if len(caps) >= 3: cap = med(caps)
    elif len(digs) >= 3: cap = med(digs)
    elif len(xhs) >= 3: cap = med(xhs) * 1.65
    else: cap = med(H("".join(c["label"] for c in clusters if c["label"])))
    xh = med(xhs) if len(xhs) >= 3 else cap * 0.6
    bank_path = arg("--bank")
    bank = json.load(open(bank_path)) if bank_path and os.path.exists(bank_path) else {"glyphs": {}}
    n = 0
    for c in clusters:
        if not c["label"] or c["label"] == "?": continue
        st = [S[k]["pts"] for k in c["ids"]]
        xs = [p[0] for t in st for p in t]; ys = [p[1] for t in st for p in t]
        x0, y0 = min(xs), min(ys)
        bank["glyphs"].setdefault(c["label"], []).append({
            "st": [[[round(p[0] - x0, 2), round(p[1] - y0, 2)] for p in t] for t in st],
            "w": round(max(xs) - x0, 2), "h": round(max(ys) - y0, 2),
            "cap": round(cap, 2), "xh": round(xh, 2), "pen": S[c["ids"][0]].get("w", 0.85)})
        n += 1
    json.dump(bank, open(bank_path, "w"), ensure_ascii=False)
    print("added %d glyphs (sample cap height %.1f pt, x-height %.1f pt)" % (n, cap, xh))
    print("bank now has:", "".join(sorted(bank["glyphs"])), " variants:", {k: len(v) for k, v in sorted(bank["glyphs"].items()) if len(v) > 1})

if __name__ == "__main__":
    main()
