"""配乐分析：响度曲线 + 强音位置 + 整体响度，并可切出试听片段。只需 ffmpeg，不需要 numpy/librosa。

为什么不用 BPM：很多钢琴曲、抒情曲是自由速度，按拍子算会不准。
直接按实测"强音"卡动作，按"低谷"放转场/对白，按"渐弱"收尾。

用法：
  python scripts/analyze_music.py music.mp3                           # 全曲每 2 秒一格
  python scripts/analyze_music.py music.mp3 --start 0 --length 34 --step 0.5   # 某段细看
  python scripts/analyze_music.py music.mp3 --cut 0 32 --fade-out 4 --out preview_A.wav
"""
import argparse
import re
import subprocess
import sys


def series(path, start, length, step, key):
    n = max(1, int(8000 * step))
    cmd = ["ffmpeg", "-v", "error"]
    if start:
        cmd += ["-ss", str(start)]
    if length:
        cmd += ["-t", str(length)]
    cmd += ["-i", path, "-af",
            f"pan=mono|c0=0.5*c0+0.5*c1,aresample=8000,asetnsamples={n},"
            f"astats=metadata=1:reset=1,ametadata=print:key=lavfi.astats.Overall.{key}:file=-",
            "-f", "null", "-"]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    ts = [float(x) + start for x in re.findall(r"pts_time:([0-9.]+)", out)]
    vs = []
    for x in re.findall(rf"{key}=(-?[0-9.]+|-inf)", out):
        vs.append(-120.0 if x == "-inf" else float(x))
    return list(zip(ts, vs))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("music")
    ap.add_argument("--start", type=float, default=0)
    ap.add_argument("--length", type=float, default=0)
    ap.add_argument("--step", type=float, default=2.0, help="每格秒数")
    ap.add_argument("--attack-db", type=float, default=6, help="峰值比上一格高出多少 dB 算强音")
    ap.add_argument("--cut", nargs=2, type=float, metavar=("START", "LEN"), help="切出试听片段")
    ap.add_argument("--fade-out", type=float, default=3)
    ap.add_argument("--out", help="试听片段输出文件")
    a = ap.parse_args()

    if a.cut:
        if not a.out:
            sys.exit("--cut 需要 --out")
        s, ln = a.cut
        fo = max(0, ln - a.fade_out)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(s), "-t", str(ln), "-i", a.music,
                        "-af", f"afade=t=in:st=0:d=0.3,afade=t=out:st={fo}:d={a.fade_out}", a.out], check=True)
        print(f"试听片段：{a.out}（原曲 {s}s 起 {ln}s，末尾 {a.fade_out}s 淡出）")
        return

    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", a.music, "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    i = re.search(r"I:\s+(-?[0-9.]+) LUFS", r)
    lra = re.search(r"LRA:\s+([0-9.]+) LU", r)
    print(f"整体响度 {i.group(1) if i else '?'} LUFS，动态范围 {lra.group(1) if lra else '?'} LU\n")

    rms = series(a.music, a.start, a.length, a.step, "RMS_level")
    print(f"== 响度曲线（每 {a.step}s，dBFS）==")
    for t, v in rms:
        print(f"{int(t // 60)}:{t % 60:05.2f}  {v:6.1f}  " + "#" * max(0, int(v + 55)))
    lo = min(rms, key=lambda x: x[1]) if rms else None
    hi = max(rms, key=lambda x: x[1]) if rms else None
    if lo and hi:
        print(f"\n最轻 {lo[0]:.2f}s（{lo[1]:.1f}）  最响 {hi[0]:.2f}s（{hi[1]:.1f}）")

    pk = series(a.music, a.start, a.length, 0.2, "Peak_level")
    attacks = [(t, v) for (t, v), (_, pv) in zip(pk[1:], pk[:-1]) if v > pv + a.attack_db and v > -30]
    if attacks:
        print("强音（候选卡点）：" + "  ".join(f"{t:.1f}s({v:.0f})" for t, v in attacks))
    print("\n提示：以上是按音量测的，'哪一下该动'最后要用耳朵确认。")


if __name__ == "__main__":
    main()
