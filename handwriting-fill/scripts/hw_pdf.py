"""Tiny dependency-free PDF writer used for the debug sheets (lines + labels only)."""

def write_pdf(path, W, H, strokes, labels=()):
    # strokes: [(pts[(x, y_from_top)], (r, g, b), width)]   labels: [(x, y_from_top, text, size)]
    c = ['1 J 1 j']
    for pts, col, w in strokes:
        c.append('%.3f %.3f %.3f RG %.3f w' % (col[0], col[1], col[2], w))
        c.append('%.2f %.2f m' % (pts[0][0], H - pts[0][1]))
        for p in pts[1:]:
            c.append('%.2f %.2f l' % (p[0], H - p[1]))
        if len(pts) == 1:
            c.append('%.2f %.2f l' % (pts[0][0] + 0.01, H - pts[0][1]))
        c.append('S')
    for x, y, t, sz in labels:
        t = t.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
        c.append('BT /F1 %.1f Tf 0 0 0 rg %.2f %.2f Td (%s) Tj ET' % (sz, x, H - y, t))
    stream = '\n'.join(c).encode('latin-1', 'replace')
    objs = [b'<< /Type /Catalog /Pages 2 0 R >>',
            b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
            ('<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %.2f %.2f] /Contents 4 0 R '
             '/Resources << /Font << /F1 5 0 R >> >> >>' % (W, H)).encode(),
            b'<< /Length %d >>\nstream\n' % len(stream) + stream + b'\nendstream',
            b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    out = b'%PDF-1.4\n'; offs = []
    for i, o in enumerate(objs):
        offs.append(len(out)); out += b'%d 0 obj\n' % (i + 1) + o + b'\nendobj\n'
    x = len(out); out += b'xref\n0 %d\n0000000000 65535 f \n' % (len(objs) + 1)
    for o in offs:
        out += b'%010d 00000 n \n' % o
    out += b'trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n' % (len(objs) + 1, x)
    open(path, 'wb').write(out)
