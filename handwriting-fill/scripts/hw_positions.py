#!/usr/bin/env python3
"""List the printed text of a form with its position, to decide where to write.

usage: hw_positions.py form.pdf [--page N]
Prints one line per text run: top(pt) left(pt) right(pt) text   (origin: top-left of the page)
"""
import sys, re, subprocess, html
if len(sys.argv) < 2:
    sys.exit(__doc__)
page = int(sys.argv[sys.argv.index("--page") + 1]) if "--page" in sys.argv else 1
xml = subprocess.run(["pdftohtml", "-xml", "-stdout", "-i", "-f", str(page), "-l", str(page), sys.argv[1]],
                     capture_output=True, text=True).stdout
pw = float(re.search(r'<page[^>]*width="(\d+)"', xml).group(1))
info = subprocess.run(["pdfinfo", "-f", str(page), "-l", str(page), sys.argv[1]], capture_output=True, text=True).stdout
m = re.search(r'Page.*size:\s+([\d.]+) x ([\d.]+)', info)
k = float(m.group(1)) / pw            # pdftohtml units -> pt
print("page %.1f x %.1f pt" % (float(m.group(1)), float(m.group(2))))
for t in re.finditer(r'<text top="(\d+)" left="(\d+)" width="(\d+)" height="(\d+)"[^>]*>(.*?)</text>', xml):
    top, left, w, h = [int(v) for v in t.group(1, 2, 3, 4)]
    txt = html.unescape(re.sub(r'<[^>]+>', '', t.group(5))).strip()
    if txt:
        print("top %6.1f  bottom %6.1f  left %6.1f  right %6.1f  %s" % (top * k, (top + h) * k, left * k, (left + w) * k, txt))
