"""生成静帧（首帧/尾帧）：文生图，或传 --image 做图生图（改图、锁背景）。默认模型 Seedream。

提示词按"段"拼接，推荐顺序：镜头段 → 角色段 → 场景段 → STYLE → NO_TEXT（模板见 templates/prompts.md）。

示例：
  # 先看提示词和费用，不花钱
  python scripts/gen_image.py --prompt-file shot01_first.txt --prompt-file prompts/char_a.txt \
      --prompt-file prompts/style.txt --prompt-file prompts/no_text.txt \
      --out ep01/frames/s01/first.png --dry-run

  # 图生图：以首帧为底改出尾帧（背景保证一致）
  python scripts/gen_image.py --image ep01/frames/s01/first.png --prompt-file shot01_edit.txt \
      --out ep01/frames/s01/last.png

需要环境变量 ARK_API_KEY。输出文件已存在时拒绝覆盖。
"""
import argparse
import base64
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _ark  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--prompt", action="append", help="提示词文本，可多次")
    ap.add_argument("--prompt-file", action="append", help="提示词文件（UTF-8），可多次，按顺序拼接")
    ap.add_argument("--image", help="输入图（图生图）")
    ap.add_argument("--out", required=True)
    ap.add_argument("--size", default="1280x720", help="如 1280x720（16:9）或 720x1280（9:16）")
    ap.add_argument("--model", default="doubao-seedream-5-0-pro-260628")
    ap.add_argument("--price", type=float, default=0.30, help="单张估价（元），仅用于提示")
    ap.add_argument("--log", default="logs/image_log.jsonl")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    prompt = _ark.read_parts(a.prompt, a.prompt_file)
    if not prompt:
        sys.exit("没有提示词")
    out = Path(a.out)
    print(f"模型 {a.model}  尺寸 {a.size}  预计 {a.price:.2f} 元  {'图生图 ← ' + a.image if a.image else '文生图'}")
    print(f"输出 {out}\n---- 提示词 ----\n{prompt}\n----------------")
    if a.dry_run:
        return 0
    if out.exists():
        sys.exit(f"{out} 已存在，不覆盖（换个文件名）")
    key = _ark.get_key()
    if not key:
        sys.exit("ARK_API_KEY 未设置")

    payload = {"model": a.model, "prompt": prompt, "size": a.size,
               "response_format": "b64_json", "watermark": False}
    if a.image:
        payload["image"] = _ark.data_uri(a.image)
    entry = {"kind": "image", "model": a.model, "size": a.size, "input": a.image,
             "out": str(out), "prompt": prompt}
    t0 = time.time()
    try:
        data = _ark.request("POST", f"{_ark.ARK_BASE}/images/generations", key, payload)
        item = (data.get("data") or [{}])[0]
        out.parent.mkdir(parents=True, exist_ok=True)
        if item.get("b64_json"):
            out.write_bytes(base64.b64decode(item["b64_json"]))
        elif item.get("url"):
            _ark.download(item["url"], out)
        else:
            raise RuntimeError(f"返回里没有图片：{str(data)[:400]}")
        entry.update(ok=True, elapsed_s=round(time.time() - t0, 1), usage=data.get("usage"), cost_est=a.price)
        print(f"OK {out}  {entry['elapsed_s']}s")
    except Exception as e:
        entry.update(ok=False, error=str(e))
        print("FAIL", e)
    _ark.log(a.log, entry)
    return 0 if entry["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
