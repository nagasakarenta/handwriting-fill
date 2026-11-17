import Foundation
import CoreGraphics
// Draw pen strokes (ink.json) on top of an existing PDF. All pages are copied; the ink goes on one page.
// usage: hw_render src.pdf ink.json out.pdf [r,g,b]   (colour 0-1, default near-black)
let a = CommandLine.arguments
guard a.count >= 4 else { print("usage: hw_render src.pdf ink.json out.pdf [r,g,b]"); exit(1) }
guard let doc = CGPDFDocument(URL(fileURLWithPath: a[1]) as CFURL) else { print("cannot open", a[1]); exit(1) }
let js = try! JSONSerialization.jsonObject(with: Data(contentsOf: URL(fileURLWithPath: a[2]))) as! [String: Any]
let strokes = js["strokes"] as! [[String: Any]]
let inkPage = (js["page"] as? Int) ?? 1
var rgb: [CGFloat] = [0.04, 0.04, 0.06]
if a.count >= 5 { let p = a[4].split(separator: ",").compactMap { Double($0) }; if p.count == 3 { rgb = p.map { CGFloat($0) } } }
guard let ctx = CGContext(URL(fileURLWithPath: a[3]) as CFURL, mediaBox: nil, nil) else { print("cannot write", a[3]); exit(1) }
for n in 1...doc.numberOfPages {
    guard let page = doc.page(at: n) else { continue }
    var box = page.getBoxRect(.mediaBox)
    let H = box.height
    let boxData = Data(bytes: &box, count: MemoryLayout<CGRect>.size)
    ctx.beginPDFPage([kCGPDFContextMediaBox as String: boxData] as CFDictionary)
    ctx.drawPDFPage(page)
    if n == inkPage {
        ctx.setStrokeColor(red: rgb[0], green: rgb[1], blue: rgb[2], alpha: 1)
        ctx.setLineCap(.round); ctx.setLineJoin(.round)
        for s in strokes {
            let raw = s["pts"] as! [[Double]]
            let pts: [CGPoint] = raw.map { CGPoint(x: $0[0] + Double(box.origin.x), y: Double(H) - $0[1] + Double(box.origin.y)) }
            if pts.isEmpty { continue }
            ctx.setLineWidth(CGFloat((s["w"] as? Double) ?? 0.85))
            ctx.move(to: pts[0])
            if pts.count < 3 {
                for p in pts.dropFirst() { ctx.addLine(to: p) }
            } else {
                for i in 1..<(pts.count - 1) {
                    let mid = CGPoint(x: (pts[i].x + pts[i + 1].x) / 2, y: (pts[i].y + pts[i + 1].y) / 2)
                    ctx.addQuadCurve(to: mid, control: pts[i])
                }
                ctx.addLine(to: pts[pts.count - 1])
            }
            ctx.strokePath()
        }
    }
    ctx.endPDFPage()
}
ctx.closePDF()
print("wrote \(a[3]) (\(strokes.count) strokes on page \(inkPage))")
