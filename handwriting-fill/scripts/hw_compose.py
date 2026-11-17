#!/usr/bin/env python3
"""Lay out text in the writer's own strokes and produce the ink to draw on a form.

usage: hw_compose.py --bank bank.json --spec spec.json --out ink.json [--seed N] [--fallback skel.json]

spec.json (all positions in pt from the top-left of the page):
{
  "page": 1,                     # page of the form to write on (default 1)
  "max_x": 545,                  # right limit; longer lines are shrunk a little to fit
  "blocks": [
    {"x": 80, "y": 300,          # left edge and baseline of the first line
     "cap_height": 10,           # height of capital letters in pt (default 10)
     "leading": 23.5,            # distance between baselines (default 2.35 x cap_height)
     "lines": ["first line", {"text": "indented line", "indent": 78}]}
  ],
  "copies": [                    # optional: reuse strokes exactly as written elsewhere
    {"strokes": "old_strokes.json", "region": [190, 40, 380, 105], "dx": 0, "dy": 0}
  ]
}
Every instance of a character is redrawn with small random changes (size, slant, bend,
baseline), so repeated letters never look stamped. --seed changes the randomness.
"""
import json, math, random, sys, os

XH_SET = "acemnorsuvwxz"
# symbols: (which point of the glyph is anchored, height of that point above the baseline in cap heights)
SYM = {"_": ("mid", -0.06), ",": ("mid", -0.04), ".": ("mid", 0.03), "=": ("mid", 0.42), "-": ("mid", 0.40),
       "+": ("mid", 0.42), "'": ("top", 1.0), '"': ("top", 1.0), "(": ("mid", 0.45), ")": ("mid", 0.45),
       "*": ("mid", 0.62), ":": ("mid", 0.32), ";": ("mid", 0.25), "<": ("mid", 0.42), ">": ("mid", 0.42),
       "/": ("mid", 0.48), "%": ("mid", 0.48), "!": ("bottom", 0.0), "?": ("bottom", 0.0)}

def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default

def main():
    if "--bank" not in sys.argv or "--spec" not in sys.argv:
        sys.exit(__doc__)
    R = random.Random(int(arg("--seed", "1")))
    bank = json.load(open(arg("--bank")))["glyphs"]
    spec = json.load(open(arg("--spec")))
    fb = json.load(open(arg("--fallback"))) if arg("--fallback") else {}
    base_dir = os.path.dirname(os.path.abspath(arg("--spec")))
    pen = spec.get("pen_width") or next(iter(bank.values()))[0].get("pen", 0.85)
    max_x = spec.get("max_x", 545)
    ink = []; last = {}

    # ---- check that every character can be written, before drawing anything ----
    need = set(ch for b in spec.get("blocks", []) for ln in b["lines"]
               for ch in (ln["text"] if isinstance(ln, dict) else ln) if ch != " ")
    missing = sorted(c for c in need if c not in bank and c not in fb)
    if missing:
        sys.exit("These characters are not in the bank (and no fallback): %s\n"
                 "Ask the writer for a sample of them, or build a fallback with hw_fallback.sh." % " ".join(missing))
    from_fb = sorted(c for c in need if c not in bank)
    if from_fb:
        print("NOT the writer's own hand (font fallback):", " ".join(from_fb))

    def pick(ch):
        vs = bank[ch]; i = R.randrange(len(vs))
        if len(vs) > 1 and last.get(ch) == i: i = (i + 1) % len(vs)
        last[ch] = i; return vs[i], len(vs)

    def metrics(ch, v, cap):
        """-> (scale, y of the baseline inside the glyph box)"""
        s = cap / v["cap"]; h = v["h"]; xh = v["xh"]
        if ch in SYM:
            how, up = SYM[ch]
            ref = {"mid": h / 2, "top": 0.0, "bottom": h}[how]
            return s, ref + up * v["cap"]
        if ch.isdigit():
            if ch in "97":                       # long tails: keep the top level, let the tail hang
                s = min(s, 1.45 * cap / h); return s, cap / s
            return 1.06 * cap / h * R.uniform(0.95, 1.04), h
        if ch.isupper():
            if h < 0.88 * v["cap"]: s *= min(2.2, 0.93 * v["cap"] / h)   # capitals written small
            return s, h
        if ch in XH_SET:
            return s * (xh / h) ** 0.85, h
        if ch == "g": return s, xh * 1.0
        if ch == "j": return s, xh * 1.45
        if ch in "pqy": return s, xh * 1.1
        return s, h                              # ascenders and anything else sit on the line

    def warp_params(size, strength):
        k = 2 * math.pi / (size * 1.3)
        return (size * strength,
                [(k * R.uniform(0.45, 1.2) * R.choice((-1, 1)), k * R.uniform(0.45, 1.2), R.uniform(0, 6.28)) for _ in range(4)])

    def place(strokes_xy_up, x, base, cap, n_var, delicate=False):
        """strokes in pt, y up from the baseline -> page coordinates with per-instance variation"""
        lo, hi = (0.008, 0.016) if delicate else ((0.02, 0.045) if n_var < 3 else (0.012, 0.028))
        amp, w = warp_params(cap, R.uniform(lo, hi))
        sx = 1 + R.gauss(0, 0.05); sy = 1 + R.gauss(0, 0.055)
        slant = R.gauss(0, 0.04); rot = R.gauss(0, 0.02 if delicate else 0.035)
        cr, sr = math.cos(rot), math.sin(rot); out = []
        for t in strokes_xy_up:
            ex = R.gauss(0, 0.3); ey = R.gauss(0, 0.3); pts = []
            for X, Y in t:
                X *= sx; Y *= sy
                X += amp * (math.sin(w[0][0] * X + w[0][1] * Y + w[0][2]) + 0.3 * math.sin(1.7 * (w[1][0] * X + w[1][1] * Y) + w[1][2]))
                Y += amp * (math.sin(w[2][0] * X + w[2][1] * Y + w[2][2]) + 0.3 * math.sin(1.7 * (w[3][0] * X + w[3][1] * Y) + w[3][2]))
                X += slant * Y
                pts.append((x + X * cr - Y * sr + ex, base - (X * sr + Y * cr) + ey))
            if len(pts) == 1: pts.append((pts[0][0] + 0.4, pts[0][1] + 0.5))
            out.append(pts)
        return out, sx

    def glyph(ch, x, base, cap):
        if ch in bank:
            v, n = pick(ch); s, by = metrics(ch, v, cap)
            st = [[(p[0] * s, (by - p[1]) * s) for p in t] for t in v["st"]]
            out, sx = place(st, x, base, cap, n, delicate=ch.isdigit())
            return out, v["w"] * s * sx
        g = fb[ch]; em = cap / 0.72
        st = [[(u * em, v_ * em) for u, v_ in t] for t in g["strokes"]]
        out, sx = place(st, x, base, cap, 3)
        return out, g["adv"] * em * sx * 0.9

    def est(text, cap):
        w = 0.0
        for ch in text:
            if ch == " ": w += cap * 0.78
            elif ch in bank: v = bank[ch][0]; w += v["w"] * cap / v["cap"] + 1.6
            else: w += cap * 0.75
        return w

    def write(text, x, y, cap):
        slope = R.gauss(0, 0.006); wander = 0.0; drift = 1.0; pen_x = x
        for ch in text:
            if ch == " ":
                pen_x += cap * R.uniform(0.62, 0.95); drift = min(1.07, max(0.94, drift + R.gauss(0, 0.02))); continue
            wander = max(-2.2, min(2.2, wander * 0.93 + R.gauss(0, 0.36)))
            base = y - slope * (pen_x - x) + wander + R.gauss(0, 0.3)
            st, adv = glyph(ch, pen_x, base, cap * drift * (1 + R.gauss(0, 0.035)))
            pen_x += adv + R.uniform(1.0, 2.2) * cap / 10
            for s in st:
                ink.append({"w": pen, "pts": [[round(a, 2), round(b, 2)] for a, b in s]})

    # ---- strokes copied as written (name, ID, signature fields the writer filled in before) ----
    for c in spec.get("copies", []):
        src = json.load(open(os.path.join(base_dir, c["strokes"])))
        x0, y0, x1, y1 = c["region"]
        part = [t for t in src if x0 <= sum(p[0] for p in t["pts"]) / len(t["pts"]) <= x1
                and y0 <= sum(p[1] for p in t["pts"]) / len(t["pts"]) <= y1]
        if not part: sys.exit("copy region %s holds no strokes" % c["region"])
        n = sum(len(t["pts"]) for t in part)
        cx = sum(p[0] for t in part for p in t["pts"]) / n; cy = sum(p[1] for t in part for p in t["pts"]) / n
        sc = R.uniform(0.96, 1.01); dx = c.get("dx", 0) + R.uniform(-3, 3); dy = c.get("dy", 0) + R.uniform(-0.8, 1.0)
        th = R.gauss(0, 0.006)
        for t in part:
            pts = []
            for x, y in t["pts"]:
                u = (x - cx) * sc; v = (y - cy) * sc
                pts.append([round(cx + dx + u * math.cos(th) - v * math.sin(th), 2), round(cy + dy + u * math.sin(th) + v * math.cos(th), 2)])
            ink.append({"w": t.get("w", pen), "pts": pts})

    # ---- text blocks ----
    for b in spec.get("blocks", []):
        cap0 = b.get("cap_height", 10); lead = b.get("leading", cap0 * 2.35)
        y = b["y"] + R.uniform(-2, 2); x0 = b["x"] + R.uniform(-5, 6)
        for ln in b["lines"]:
            text, indent = (ln["text"], ln.get("indent", 0)) if isinstance(ln, dict) else (ln, 0)
            x = x0 + R.uniform(-3.5, 3.5) + (indent + R.uniform(-8, 8) if indent else 0)
            cap = cap0 * (1 + R.uniform(-0.035, 0.04))
            ew = est(text, cap)
            if x + ew > max_x: cap *= max(0.78, (max_x - x) / ew)
            write(text, x, y, cap); y += lead + R.uniform(-1.5, 1.6)
    json.dump({"page": spec.get("page", 1), "strokes": ink}, open(arg("--out"), "w"))
    print("ink strokes:", len(ink))

if __name__ == "__main__":
    main()
