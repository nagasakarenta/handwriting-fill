---
name: handwriting-fill
description: Fill in a PDF form, worksheet or answer sheet in the user's OWN handwriting, by reusing the real pen strokes from PDFs they exported from a note-taking app (GoodNotes, Notability, Apple Notes, etc.) and writing new text with them. Use this whenever the user wants typed text to appear handwritten on a PDF, says things like "write this in my handwriting", "fill this sheet in by hand", "make it look handwritten", "手書き風で記入して", "自分の字で書き込んで", "GoodNotesで書いたみたいに", or complains that a handwriting font "doesn't look handwritten" — a font can never fix that, this skill does. Also use it to build or extend the user's personal handwriting glyph bank from a sample sheet. Not for imitating anyone else's handwriting or signature.
compatibility: macOS (uses swiftc and the system PDF engine to draw) with poppler installed (pdftocairo, pdftohtml, pdftoppm, pdfinfo). Python 3, no extra packages.
---

# Handwriting fill

Write text onto a PDF using the user's own pen strokes, so the result looks like they
filled the sheet in with a stylus.

## Why it works this way

A handwriting *font* always looks fake: every "e" is the same shape, lines are dead
straight, and the outlines are thick filled shapes instead of pen lines. Jittering a font
does not fix it — users notice immediately. What does work:

- **Real strokes.** Note apps export handwriting as vector pen paths. Those paths can be
  lifted out of the PDF and replayed anywhere, at the same pen width.
- **The writer's own letter shapes**, cut out of a sample sheet into a *glyph bank*.
- **No two instances alike.** Each letter is redrawn with a small random bend, tilt and
  size change, on a baseline that wanders the way a hand does.

So the whole job is: get strokes → cut them into labelled characters → lay out the new
text → draw it on the form → look at the result.

All scripts are in `scripts/`. Coordinates everywhere are PDF points measured from the
**top-left** of the page.

## Only the user's own hand

This reproduces a person's handwriting, which is personal and can be misused. Build the
bank only from samples the user wrote themselves, and use it only on their own documents.
Decline to copy someone else's handwriting or signature. The bank and stroke files are
personal data: keep them in the user's private folder, never inside a repository or a
skill folder that might be shared.

## Step 1 — Check the tools

```bash
which pdftocairo pdftohtml pdftoppm swiftc
```

If poppler is missing: `brew install poppler`. If `swiftc` is missing the renderer cannot
run (`xcode-select --install`); say so rather than falling back to a font.

## Step 2 — Get handwriting samples

Look for what already exists before asking the user to write anything: earlier sheets they
filled in with the same app are the best source for their **name, ID and digits**, written
exactly as they write them on real forms.

For the text itself, work out the exact set of characters needed and ask only for those
(people will not write a full alphabet twice if eight letters would do). Ask the user to:

1. write them **in a stated order, one row per group** (lowercase / capitals / digits / symbols),
2. leave about **one character of space** between characters,
3. repeat each row **2–3 times** if they are willing — several variants per letter is the
   single biggest gain in realism,
4. use their **usual pen and size**, and export as **PDF, not a photo or screenshot**.

A photo or scan holds no strokes; `hw_extract.py` will report zero and say so. Tell the user
a vector export is required instead of trying to trace the image.

## Step 3 — Build the glyph bank

```bash
python3 scripts/hw_extract.py sample.pdf strokes.json
python3 scripts/hw_segment.py strokes.json \
    --rows "abcdefghij" "ABCDEFGHIJ" "0123456789" "_,=()" \
    --bank bank.json --debug debug.pdf
pdftoppm -r 80 -png debug.pdf debug     # then LOOK at debug-1.png
```

`--rows` lists what was written, top row first, in writing order. The script groups strokes
into rows, rows into blobs, and labels blobs in order. **Always open the debug image**: it
shows every blob in colour with its number, and it is the only way to know the labels are
right. A wrong label means the wrong letter gets written on the form.

When counts do not match, nothing is saved and the script says which row is off. Usual fixes:

- a stray mark or a botched attempt → put `?` at that position in the row string to skip it;
- rows merged or split (a character written below the line, big descenders) → give the
  rows explicitly: `--bands "0-100,100-145,145-208"` (y ranges are printed by the script);
- letters fused or a letter split in two → change `--gap` (pt). Larger joins more. For
  tightly written digits use a negative value such as `--gap -0.3`, meaning strokes must
  actually overlap to count as one character;
- printed rules or underlines picked up as strokes → `--max-width 100`;
- only part of a page is the sample (a filled-in form) → `--region x0,y0,x1,y1`.

Run it again on other samples with the same `--bank` to add variants. When a sheet holds
several attempts of a character, skip the unreadable ones with `?` — a sloppy "3" that
reads as "8" will be chosen at random later and can change an answer.

## Step 4 — Decide where to write

```bash
python3 scripts/hw_positions.py form.pdf
```

prints each printed text run with its top/bottom/left/right. Use it to find the blank areas:
a baseline sits a little above the underline of a field, and the first answer line usually
goes about 35–40 pt below the top of the question text. Size the writing from the space
available — count the lines that must fit between two questions. If the user has an earlier
sheet they filled in by hand, match the size they wrote at there; people write larger than
print (capital height around 10–14 pt is typical).

For a **name / ID field**, prefer copying the strokes straight from an earlier sheet with the
`copies` entry (below): it is their real signature-like writing, and forms from the same
source put the field in the same place.

## Step 5 — Compose and draw

Write a spec (JSON):

```json
{
  "page": 1,
  "max_x": 545,
  "copies": [
    {"strokes": "old_sheet_strokes.json", "region": [190, 40, 380, 105], "dy": 0}
  ],
  "blocks": [
    {"x": 76, "y": 298, "cap_height": 10, "leading": 23.5,
     "lines": ["first line of the answer",
               {"text": "a continuation line", "indent": 78}]}
  ]
}
```

- `blocks`: `x`,`y` = left edge and baseline of the first line; `cap_height` = height of a
  capital letter in pt; `leading` = distance between baselines.
- `copies`: strokes inside `region` of another stroke file are placed at the same spot
  (shifted by `dx`,`dy`), with a tiny random shift so it is not a pixel-identical duplicate.
- `max_x`: lines that would run past it are shrunk slightly, the way people squeeze a long line.

```bash
python3 scripts/hw_compose.py --bank bank.json --spec spec.json --out ink.json --seed 1
bash scripts/hw_render.sh form.pdf ink.json filled.pdf
pdftoppm -r 110 -png filled.pdf check   # then LOOK at it
```

The original form is never modified; the result is a new file. A different `--seed` gives a
different "take" of the same text — try another if a letter came out badly.

`hw_compose.py` stops before drawing if a needed character is missing from the bank and
lists them. Either ask the user for those characters, or build a font-based stand-in:

```bash
bash scripts/hw_fallback.sh /path/to/a-monoline-handwriting-font.ttf "vxz" skel.json
python3 scripts/hw_compose.py ... --fallback skel.json
```

Stand-in letters are thin pen lines traced from the font, so they blend in, but they are not
the writer's hand and look neater than the rest. The script prints which characters used the
fallback — pass that on to the user.

## Step 6 — Check before handing over

Look at the rendered page, zooming in on anything that must be exact: ID numbers, digits,
quoted strings, names. Compare character by character with the intended text. Then tell the
user plainly:

- which characters are their own strokes and which are stand-ins;
- anything that is hard to read. Real handwriting is often ambiguous (an "i" that looks like
  "c", a "d" like an arrow). That is faithful, but on an answer sheet it can cost marks, so
  point it out and offer to swap in a re-written sample of just those letters;
- that nothing has been submitted or sent — writing on the sheet and handing it in are
  separate decisions.

## Files this produces

Keep them together in the user's own folder so the next sheet takes minutes:

| file | what it is |
| --- | --- |
| `*_strokes.json` | raw pen strokes of one sample page |
| `bank.json` | the glyph bank: character → list of variants |
| `*_spec.json` | what was written where on one form |
| `ink.json` | the strokes to draw (regenerated each run) |
