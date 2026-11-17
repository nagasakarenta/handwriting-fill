import Foundation
import CoreGraphics
import CoreText
// Rasterise glyphs of a font to pixel lists (input for hw_skeleton.py). usage: hw_glyphdump font.ttf "chars" out.json
let args = CommandLine.arguments
let fontURL = URL(fileURLWithPath: args[1])
let chars = Array(args[2])
let em: CGFloat = 200
let W = Int(em * 1.7), Hh = Int(em * 1.7)
let ox: CGFloat = em * 0.3, oy: CGFloat = em * 0.45
guard let prov = CGDataProvider(url: fontURL as CFURL), let cgfont = CGFont(prov) else { fatalError("font") }
let font = CTFontCreateWithGraphicsFont(cgfont, em, nil, nil)
var out: [String: Any] = [:]
for ch in chars {
    var uni = Array(String(ch).utf16)
    var glyphs = [CGGlyph](repeating: 0, count: uni.count)
    CTFontGetGlyphsForCharacters(font, &uni, &glyphs, uni.count)
    var adv = CGSize.zero
    CTFontGetAdvancesForGlyphs(font, .horizontal, &glyphs, &adv, 1)
    var data = [UInt8](repeating: 255, count: W * Hh)
    let cs = CGColorSpaceCreateDeviceGray()
    var fg: [[Int]] = []
    data.withUnsafeMutableBytes { buf in
        let ctx = CGContext(data: buf.baseAddress, width: W, height: Hh, bitsPerComponent: 8, bytesPerRow: W, space: cs, bitmapInfo: CGImageAlphaInfo.none.rawValue)!
        ctx.setFillColor(gray: 1, alpha: 1); ctx.fill(CGRect(x: 0, y: 0, width: W, height: Hh))
        ctx.setFillColor(gray: 0, alpha: 1)
        if let gp = CTFontCreatePathForGlyph(font, glyphs[0], nil) {
            ctx.translateBy(x: ox, y: oy); ctx.addPath(gp); ctx.fillPath()
        }
    }
    for r in 0..<Hh { for c in 0..<W { if data[r * W + c] < 128 { fg.append([c, r]) } } }
    out[String(ch)] = ["adv": Double(adv.width / em), "fg": fg]
}
let meta: [String: Any] = ["em": Double(em), "ox": Double(ox), "baseRow": Double(CGFloat(Hh) - oy), "glyphs": out]
let js = try! JSONSerialization.data(withJSONObject: meta)
try! js.write(to: URL(fileURLWithPath: args[3]))
print("dumped", out.count)
