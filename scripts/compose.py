"""按时间线 JSON 一次合成整集：剪辑 → 定格补帧 → 黑场 → 字幕 → 配音 → 配乐自动避让 → 响度统一 → 导出。

时间线格式见 examples/timeline.example.json，要点：
  shots  : [{"file", "in", "out", "hold"}]   按顺序首尾相接；hold = 末尾定格秒数
  tail_black : 片尾黑场秒数
  lines  : [{"id" 或 "file", "at", "text", ...}]   at = 人声在成片里的起点（秒）
           配合 lines_file（make_voice.py 产出的 lines_measured.json）自动取 lead/length
  texts  : [{"start", "end", "text", "position", "size"}]   不配音的纯字幕（片名、提示）
  music  : {"file", "start", "fade_out", "lufs"}           配乐，人声出现时自动压低

字幕规则：人声前 0.1s 出，人声后 0.6s 收；不跨镜头切点，不压到下一句。

用法：
  python scripts/compose.py examples/timeline.example.json
  python scripts/compose.py timeline.json --print-cmd      # 只打印 ffmpeg 命令
依赖：ffmpeg（含 libx264、drawtext）。
"""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def ff_path(p):
    return str(p).replace("\\", "/").replace(":", "\\:")


def load(path):
    cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    base = Path(path).resolve().parent
    rel = lambda p: str((base / p).resolve()) if p and not Path(p).is_absolute() else p  # noqa: E731
    for s in cfg["shots"]:
        s["file"] = rel(s["file"])
    measured = {}
    if cfg.get("lines_file"):
        lf = Path(rel(cfg["lines_file"]))
        for m in json.loads(lf.read_text(encoding="utf-8")):
            m["file"] = str((lf.parent / m["file"]).resolve())   # 测量文件里的音频路径相对它自己
            measured[m["id"]] = m
    lines = []
    for ln in cfg.get("lines", []):
        if "file" in ln:
            ln = {**ln, "file": rel(ln["file"])}
        m = {**measured.get(ln.get("id"), {}), **ln}
        if "file" not in m:
            sys.exit(f"台词 {ln.get('id')} 找不到音频（缺 file，lines_file 里也没有）")
        m.setdefault("lead", 0.0)
        m.setdefault("volume", 1.0)
        if "length" not in m:
            sys.exit(f"台词 {ln.get('id')} 缺 length（先用 make_voice.py 测量）")
        lines.append(m)
    cfg["lines"] = sorted(lines, key=lambda x: x["at"])
    if cfg.get("music"):
        cfg["music"]["file"] = rel(cfg["music"]["file"])
    cfg["output"] = rel(cfg.get("output", "output.mp4"))
    return cfg


def build(cfg, tmp):
    W, H, FPS = cfg.get("width", 1280), cfg.get("height", 720), cfg.get("fps", 24)
    font = ff_path(cfg.get("font", "C:/Windows/Fonts/msyh.ttc"))
    sub = {"size": 40 if W >= H else 52, "margin": 60 if W >= H else 220, **cfg.get("subtitle", {})}
    cmd = ["ffmpeg", "-v", "error", "-y"]
    for s in cfg["shots"]:
        cmd += ["-i", s["file"]]
    parts, labels, t, cuts = [], [], 0.0, []
    for i, s in enumerate(cfg["shots"]):
        c = (f"[{i}:v]trim=start={s.get('in', 0)}:end={s['out']},setpts=PTS-STARTPTS,"
             f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,"
             f"fps={FPS},format=yuv420p")
        if s.get("hold"):
            c += f",tpad=stop_mode=clone:stop_duration={s['hold']}"
        parts.append(c + f"[v{i}]")
        labels.append(f"[v{i}]")
        d = s["out"] - s.get("in", 0) + s.get("hold", 0)
        print(f"  镜{i + 1:02d} {Path(s['file']).name}: 素材 {s.get('in', 0):.2f}–{s['out']:.2f}  →  成片 {t:.2f}–{t + d:.2f}")
        t += d
        cuts.append(round(t, 3))
    black = cfg.get("tail_black", 0)
    if black:
        parts.append(f"color=c=black:s={W}x{H}:r={FPS}:d={black},format=yuv420p[vb]")
        labels.append("[vb]")
    total = round(t + black, 3)
    cuts.append(total)
    parts.append("".join(labels) + f"concat=n={len(labels)}:v=1:a=0[vc]")

    # 字幕
    subs = []
    L = cfg["lines"]
    for k, ln in enumerate(L):
        if not ln.get("text"):
            continue
        s = max(0.0, ln["at"] - 0.1)
        e = ln["at"] + ln["length"] + 0.6
        if k + 1 < len(L):
            e = min(e, L[k + 1]["at"] - 0.05)
        nxt_cut = min((c for c in cuts if c > ln["at"]), default=total)
        if ln.get("cross_cut") is not True:
            e = min(e, nxt_cut - 0.05)
        subs.append((round(s, 2), round(e, 2), ln["text"], ln.get("position", "bottom"), ln.get("size")))
    for x in cfg.get("texts", []):
        subs.append((x["start"], x["end"], x["text"], x.get("position", "bottom"), x.get("size")))
    draws = []
    for k, (s, e, text, pos, size) in enumerate(subs):
        tf = Path(tmp) / f"sub{k:02d}.txt"
        tf.write_text(text, encoding="utf-8")
        y = f"h-th-{sub['margin']}" if pos == "bottom" else "(h-th)/2" if pos == "center" else f"{sub['margin']}"
        fs = size or (sub["size"] if pos != "center" else int(sub["size"] * 1.3))
        draws.append(f"drawtext=fontfile='{font}':textfile='{ff_path(tf)}':fontsize={fs}:fontcolor=white"
                     f":borderw=2:bordercolor=black@0.7:x=(w-tw)/2:y={y}"
                     f":alpha='if(lt(t,{s}+0.25),(t-{s})/0.25,if(gt(t,{e}-0.25),({e}-t)/0.25,1))'"
                     f":enable='between(t,{s},{e})'")
        print(f"  字幕 {s:6.2f}–{e:6.2f}  {text}")
    parts.append("[vc]" + (",".join(draws) if draws else "null") + "[vout]")

    # 音频
    n_in = len(cfg["shots"])
    music, alabel = cfg.get("music"), None
    if music:
        cmd += ["-ss", str(music.get("start", 0)), "-i", music["file"]]
        mi = n_in
        n_in += 1
        fo = music.get("fade_out", 3)
        parts.append(f"[{mi}:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{total},"
                     f"afade=t=out:st={max(0, total - fo)}:d={fo},"
                     f"loudnorm=I={music.get('lufs', -24 if L else -16)}:TP=-3:LRA=11,aresample=48000[m]")
        alabel = "[m]"
    if L:
        vl = []
        for k, ln in enumerate(L):
            cmd += ["-i", ln["file"]]
            ms = max(0, int(round((ln["at"] - ln["lead"]) * 1000)))
            parts.append(f"[{n_in}:a]aresample=48000,aformat=channel_layouts=stereo,volume={ln['volume']},"
                         f"adelay={ms}|{ms}[l{k}]")
            vl.append(f"[l{k}]")
            n_in += 1
        parts.append("".join(vl) + f"amix=inputs={len(vl)}:normalize=0,apad=whole_dur={total},atrim=0:{total},"
                     f"loudnorm=I={cfg.get('voice_lufs', -16)}:TP=-2:LRA=7,aresample=48000[vo]")
        if alabel:
            parts.append("[vo]asplit=2[vomix][vokey]")
            parts.append(f"[m][vokey]sidechaincompress=threshold=0.02:ratio={cfg.get('duck_ratio', 5)}"
                         f":attack=30:release=600[md]")
            parts.append("[md][vomix]amix=inputs=2:normalize=0[mix]")
            alabel = "[mix]"
        else:
            alabel = "[vo]"
    if alabel:
        parts.append(f"{alabel}alimiter=limit=0.89,aresample=48000[aout]")
    else:
        parts.append(f"anullsrc=r=48000:cl=stereo,atrim=0:{total}[aout]")

    cmd += ["-filter_complex", ";".join(parts), "-map", "[vout]", "-map", "[aout]", "-t", str(total),
            "-c:v", "libx264", "-crf", str(cfg.get("crf", 18)), "-preset", "medium", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart"]
    if cfg.get("title"):
        cmd += ["-metadata", f"title={cfg['title']}"]
    cmd.append(cfg["output"])
    return cmd, total


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("timeline")
    ap.add_argument("--print-cmd", action="store_true")
    a = ap.parse_args()
    cfg = load(a.timeline)
    out = Path(cfg["output"])
    if out.exists() and not cfg.get("overwrite"):
        sys.exit(f"{out} 已存在，不覆盖（改 output 或在时间线里设 \"overwrite\": true）")
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        cmd, total = build(cfg, tmp)
        if a.print_cmd:
            print(subprocess.list2cmdline(cmd))
            return
        print(f"合成 → {out}（{total:.2f}s）")
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode:
            sys.exit(r.stderr[-1500:])
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(out), "-af", "ebur128=peak=true",
                        "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    stats = [x.strip() for x in r.stderr.splitlines() if x.strip().startswith(("I:", "Peak:"))]
    print("完成。" + "  ".join(stats))


if __name__ == "__main__":
    main()
