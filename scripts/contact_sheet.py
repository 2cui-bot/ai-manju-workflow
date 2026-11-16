"""逐帧审片：把视频拆成带时间戳的帧条，并自动检测跳场。不花钱，只需 ffmpeg。

用途：
  - 看清每个动作发生在第几秒（剪辑卡点要用）
  - 找出可用区间、变形、换脸
  - scene 检测：画面突变的时间点（> 阈值即疑似跳场）

用法：
  python scripts/contact_sheet.py clip.mp4 --out sheet.png            # 默认每秒 4 帧
  python scripts/contact_sheet.py clip.mp4 --out zoom.png --start 1 --length 1.5 --fps 8
"""
import argparse
import math
import os
import re
import subprocess
import sys


def default_font():
    for f in ("C:/Windows/Fonts/arial.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.exists(f):
            return f
    return ""


def ff_path(p):
    """drawtext 里的路径：Windows 盘符冒号要转义。"""
    return p.replace("\\", "/").replace(":", "\\:")


def duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                       capture_output=True, text=True)
    return float(r.stdout.strip())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--out", required=True)
    ap.add_argument("--fps", type=float, default=4)
    ap.add_argument("--cols", type=int, default=6)
    ap.add_argument("--thumb", type=int, default=320, help="每格宽度")
    ap.add_argument("--start", type=float, default=0)
    ap.add_argument("--length", type=float, default=0, help="0 = 到结尾")
    ap.add_argument("--scene", type=float, default=0.2, help="跳场检测阈值 0–1")
    ap.add_argument("--font", default=default_font())
    a = ap.parse_args()

    total = duration(a.video)
    length = a.length or (total - a.start)
    n = max(1, math.ceil(length * a.fps))
    rows = math.ceil(n / a.cols)
    label = ""
    if a.font:
        label = (f",drawtext=fontfile='{ff_path(a.font)}':text='%{{pts\\:flt}}':x=6:y=6:fontsize=20"
                 f":fontcolor=yellow:box=1:boxcolor=black@0.6")
    vf = f"fps={a.fps},scale={a.thumb}:-1{label},tile={a.cols}x{rows}"
    cmd = ["ffmpeg", "-v", "error", "-y", "-ss", str(a.start), "-t", str(length), "-i", a.video,
           "-vf", vf, "-frames:v", "1", a.out]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.exit(r.stderr[-800:])
    print(f"帧条：{a.out}（{n} 帧，{a.cols}×{rows}；格子里的时间从 --start 起算）")

    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", a.video, "-vf",
                        f"select='gt(scene,{a.scene})',showinfo", "-an", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    cuts = re.findall(r"pts_time:([0-9.]+)", r.stderr)
    if cuts:
        print(f"⚠ 疑似跳场（scene>{a.scene}）：" + "、".join(f"{float(t):.2f}s" for t in cuts))
    else:
        print(f"未检测到跳场（scene>{a.scene}），总长 {total:.2f}s")


if __name__ == "__main__":
    main()
