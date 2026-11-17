# handwriting-fill

A Claude skill that fills in PDF forms and worksheets in **your own handwriting**.

It lifts the real pen strokes out of PDFs you exported from a note-taking app (GoodNotes
and similar), cuts them into a personal glyph bank, and writes new text with them — each
letter redrawn slightly differently, on a wandering baseline, at your pen's width.

自分の字で PDF の用紙に書き込むための Claude のスキルです。GoodNotes などから書き出した
PDF に入っているペンの線を取り出して「字の辞書」を作り、その線で新しい文を書きます。
同じ字でも毎回少し形を変えるので、フォントのような不自然さが出ません。

## Requirements / 動作環境

- macOS (the renderer uses `swiftc` and the system PDF engine)
- [poppler](https://poppler.freedesktop.org/) — `brew install poppler`
- Python 3 (no extra packages)
- Samples exported as **vector PDF** from a note app. Photos and scans do not work.

## Install / 入れ方

Copy the `handwriting-fill` folder into `~/.claude/skills/` (Claude Code), or zip it and
upload it as a skill in the Claude app settings.

## Use only your own handwriting / 自分の字だけに使ってください

The glyph bank is a copy of how you write. Build it only from your own samples, use it on
your own documents, and keep it out of anything you share. Do not use this to imitate
another person's handwriting or signature.

No handwriting data is included in this repository.

## License

MIT © 2026 longslope
