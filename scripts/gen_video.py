"""图生视频：首帧（+ 可选尾帧）+ 运动提示词 → 视频。默认模型 Seedance 2.0 mini。

运动提示词只写"怎么动"（模板见 templates/prompts.md 的 MOTION）。

示例：
  python scripts/gen_video.py --first s05/first.png --last s05/last.png \
      --motion-file s05/motion.txt --out ep01/clips/s05_v1.mp4 --dry-run   # 先报价
  python scripts/gen_video.py ...（去掉 --dry-run 才会提交并扣费）

费用估算：秒数 × 宽 × 高 × 帧率 ÷ 1024 = tokens；× 每千 tokens 单价。
单价、模型名请以平台当前价目为准（--price-per-1k、--model 可改）。
需要环境变量 ARK_API_KEY。输出文件已存在时拒绝覆盖。
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _ark  # noqa: E402

RES = {"480p": (854, 480), "720p": (1280, 720), "1080p": (1920, 1080)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--first", required=True, help="首帧图")
    ap.add_argument("--last", help="尾帧图（可选）")
    ap.add_argument("--motion", action="append", help="运动提示词文本")
    ap.add_argument("--motion-file", action="append", help="运动提示词文件")
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="doubao-seedance-2-0-mini-260615")
    ap.add_argument("--duration", type=int, default=6)
    ap.add_argument("--resolution", default="720p", choices=RES)
    ap.add_argument("--fps", type=int, default=24, help="仅用于估价")
    ap.add_argument("--price-per-1k", type=float, default=0.023, help="每千 tokens 单价（元），仅用于估价")
    ap.add_argument("--log", default="logs/video_log.jsonl")
    ap.add_argument("--timeout", type=int, default=900, help="轮询超时秒数")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    motion = _ark.read_parts(a.motion, a.motion_file)
    if not motion:
        sys.exit("没有运动提示词")
    for f in [a.first] + ([a.last] if a.last else []):
        if not Path(f).exists():
            sys.exit(f"缺图 {f}")
    w, h = RES[a.resolution]
    tokens = a.duration * w * h * a.fps / 1024
    cost = tokens / 1000 * a.price_per_1k
    out = Path(a.out)
    print(f"模型 {a.model}  {a.resolution} {a.duration}s  约 {tokens:,.0f} tokens  预计 {cost:.2f} 元")
    print(f"首帧 {a.first}  尾帧 {a.last or '（无）'}  →  {out}\n---- 运动提示词 ----\n{motion}\n--------------------")
    if a.dry_run:
        return 0
    if out.exists():
        sys.exit(f"{out} 已存在，不覆盖")
    key = _ark.get_key()
    if not key:
        sys.exit("ARK_API_KEY 未设置")

    content = [{"type": "text", "text": motion},
               {"type": "image_url", "image_url": {"url": _ark.data_uri(a.first)}, "role": "first_frame"}]
    if a.last:
        content.append({"type": "image_url", "image_url": {"url": _ark.data_uri(a.last)}, "role": "last_frame"})
    payload = {"model": a.model, "content": content, "resolution": a.resolution, "ratio": "adaptive",
               "duration": a.duration, "watermark": False, "generate_audio": False}
    entry = {"kind": "video", "model": a.model, "first": a.first, "last": a.last, "out": str(out),
             "prompt": motion, "cost_est": round(cost, 2)}
    base = f"{_ark.ARK_BASE}/contents/generations/tasks"
    t0 = time.time()
    try:
        tid = _ark.request("POST", base, key, payload, timeout=120).get("id")
        entry["task_id"] = tid
        print(f"task_id={tid}，轮询中 ...", flush=True)
        while True:
            d = _ark.request("GET", f"{base}/{tid}", key, timeout=60)
            st = d.get("status")
            if st in ("succeeded", "failed", "cancelled", "expired"):
                break
            if time.time() - t0 > a.timeout:
                raise RuntimeError(f"轮询超时（task 仍在跑，可稍后用 task_id 查询）：{tid}")
            time.sleep(10)
        if st != "succeeded":
            raise RuntimeError(f"status={st} {str(d)[:600]}")
        url = (d.get("content") or {}).get("video_url")
        if not url:
            raise RuntimeError(f"返回里没有 video_url：{str(d)[:400]}")
        out.parent.mkdir(parents=True, exist_ok=True)
        _ark.download(url, out)
        entry.update(ok=True, elapsed_s=round(time.time() - t0, 1), usage=d.get("usage"))
        print(f"OK {out}  {entry['elapsed_s']}s")
    except Exception as e:
        entry.update(ok=False, error=str(e))
        print("FAIL", e)
    _ark.log(a.log, entry)
    return 0 if entry["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
