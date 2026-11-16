"""首尾帧自动检查：差异数值 + 分区报告 + 对照图。提交视频前用，不花钱。

输出到 --out-dir：
  report.txt      全图平均差异、变化像素占比、3×4 分区差异、判定
  side_by_side.png 并排对照
  overlay.png      50% 叠加（查错位）
  heatmap.png      差异热力图（越亮差越多）
  phone.png        缩到手机宽度（查远处人物是否看得清）
  corners.png      四角放大（查多余物件/水印）

经验阈值（同一机位的首尾帧）：
  全图平均 > 50        几乎肯定不是同一地点 → 视频中途跳场，必须改
  平均 ≈ 10–20 且差异集中在"要动的区域"   合格
  不该动的分区 > 20    该区域会在视频里慢慢变形，建议改

用法：python scripts/check_frames.py first.png last.png --out-dir check/s05
依赖：pip install pillow numpy
"""
import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("first")
    ap.add_argument("last")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--rows", type=int, default=3)
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--phone-width", type=int, default=390)
    a = ap.parse_args()

    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    A = Image.open(a.first).convert("RGB")
    B = Image.open(a.last).convert("RGB")
    if A.size != B.size:
        print(f"注意：尺寸不同 {A.size} vs {B.size}，尾帧已缩放到首帧尺寸再比较")
        B = B.resize(A.size, Image.LANCZOS)
    w, h = A.size
    D = np.abs(np.asarray(A, float) - np.asarray(B, float)).mean(2)
    mean = D.mean()
    changed = (D > 12).mean() * 100

    lines = [f"首帧 {a.first}", f"尾帧 {a.last}", f"尺寸 {w}x{h}",
             f"全图平均差异 {mean:.2f}    变化像素(>12) {changed:.1f}%", "",
             f"分区平均差异（{a.rows}×{a.cols}，从左上开始）："]
    grid = []
    for r in range(a.rows):
        row = [D[r * h // a.rows:(r + 1) * h // a.rows, c * w // a.cols:(c + 1) * w // a.cols].mean()
               for c in range(a.cols)]
        grid.append(row)
        lines.append("  " + "  ".join(f"{v:6.1f}" for v in row))
    lines.append("")
    if mean > 50:
        verdict = "✗ 不合格：首尾帧很可能不是同一地点/机位，视频会中途跳场。建议以一张为底图做图生图得到另一张。"
    elif mean > 25:
        verdict = "△ 偏大：检查是否有不该变的区域（背景、光线、道具）在变。"
    else:
        verdict = "✓ 整体差异正常。再确认差异最大的分区正是'要动的区域'。"
    hot = sorted(((v, r, c) for r, row in enumerate(grid) for c, v in enumerate(row)), reverse=True)[:3]
    lines.append(verdict)
    lines.append("差异最大的分区：" + "，".join(f"第{r + 1}行第{c + 1}列({v:.1f})" for v, r, c in hot))
    (out / "report.txt").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))

    sbs = Image.new("RGB", (w * 2 + 10, h), "white")
    sbs.paste(A, (0, 0))
    sbs.paste(B, (w + 10, 0))
    sbs.save(out / "side_by_side.png")
    Image.blend(A, B, 0.5).save(out / "overlay.png")
    hm = np.clip(D * 3, 0, 255).astype(np.uint8)
    heat = Image.fromarray(np.stack([hm, (hm * 0.4).astype(np.uint8), 255 - hm], 2))
    dr = ImageDraw.Draw(heat)
    for r in range(1, a.rows):
        dr.line([(0, r * h // a.rows), (w, r * h // a.rows)], fill="white")
    for c in range(1, a.cols):
        dr.line([(c * w // a.cols, 0), (c * w // a.cols, h)], fill="white")
    heat.save(out / "heatmap.png")
    pw = a.phone_width
    ph = round(h * pw / w)
    phone = Image.new("RGB", (pw * 2 + 10, ph), "white")
    phone.paste(A.resize((pw, ph), Image.LANCZOS), (0, 0))
    phone.paste(B.resize((pw, ph), Image.LANCZOS), (pw + 10, 0))
    phone.save(out / "phone.png")
    # 四角各放大 2 倍，按 左上/右上/左下/右下 排成一行；第一行首帧、第二行尾帧
    cw, ch = w // 5, h // 5
    corners = Image.new("RGB", (cw * 2 * 4, ch * 2 * 2 + 10), "white")
    for i, img in enumerate((A, B)):
        for j, (x, y) in enumerate([(0, 0), (w - cw, 0), (0, h - ch), (w - cw, h - ch)]):
            corners.paste(img.crop((x, y, x + cw, y + ch)).resize((cw * 2, ch * 2)),
                          (j * cw * 2, i * (ch * 2 + 10)))
    corners.save(out / "corners.png")
    print(f"\n对照图已写入 {out}/（第一行首帧四角，第二行尾帧四角）")


if __name__ == "__main__":
    main()
