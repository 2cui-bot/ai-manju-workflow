"""批量配音（edge-tts，免费）+ 量出每句真正发声的起止时间，供 compose.py 精确对位。

输入 lines.json（示例见 examples/lines.example.json）：
  [{"id": "01", "voice": "zh-CN-YunxiNeural", "rate": "-10%", "pitch": "+0Hz", "text": "……"}, ...]

输出：
  <out-dir>/<id>.mp3
  <out-dir>/lines_measured.json   每句加上 file / lead（开头静音秒）/ length（发声秒）

常用中文音色：zh-CN-YunxiNeural（青年男）、zh-CN-XiaoxiaoNeural（温暖女）、
zh-CN-XiaoyiNeural（活泼女/少女）、zh-CN-YunxiaNeural（男童）、zh-CN-YunjianNeural（激情男）、
zh-CN-YunyangNeural（新闻男）。完整列表：python -m edge_tts --list-voices

用法：python scripts/make_voice.py examples/lines.example.json --out-dir ep01/voice
依赖：pip install edge-tts（需要能访问微软语音服务）
其他 TTS：只要把音频放到 <out-dir>/<id>.mp3，再加 --measure-only 即可只做测量。
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


def measure(path, noise_db=-45, min_sil=0.1):
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                str(path)], capture_output=True, text=True).stdout.strip())
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af",
                          f"silencedetect=n={noise_db}dB:d={min_sil}", "-f", "null", "-"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    starts = [float(x) for x in re.findall(r"silence_start: ([0-9.]+)", err)]
    ends = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", err)]
    ends += [dur] * (len(starts) - len(ends))          # 有的 ffmpeg 版本不打印结尾处的 silence_end
    sil = list(zip(starts, ends))
    lead = sil[0][1] if sil and sil[0][0] < 0.05 else 0.0
    tail = sil[-1][0] if sil and sil[-1][1] >= dur - 0.05 and sil[-1][0] > lead else dur
    return round(lead, 3), round(max(0.0, tail - lead), 3), round(dur, 3)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("lines")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--measure-only", action="store_true")
    ap.add_argument("--overwrite", action="store_true")
    a = ap.parse_args()

    lines = json.loads(Path(a.lines).read_text(encoding="utf-8"))
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    result = []
    for ln in lines:
        f = out / f"{ln['id']}.mp3"
        if not a.measure_only and (a.overwrite or not f.exists()):
            cmd = [sys.executable, "-m", "edge_tts", "--voice", ln["voice"], f"--rate={ln.get('rate', '+0%')}",
                   f"--pitch={ln.get('pitch', '+0Hz')}", "--text", ln["text"], "--write-media", str(f)]
            r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
            if r.returncode:
                print(f"FAIL {ln['id']}: {r.stderr.strip()[-300:]}")
                continue
        if not f.exists():
            print(f"缺 {f}")
            continue
        lead, length, dur = measure(f)
        result.append({**ln, "file": f.name, "lead": lead, "length": length, "duration": dur})
        cps = len(re.sub(r"[\s，。？！、…,.?!]", "", ln["text"])) / length if length else 0
        print(f"{ln['id']}: 开头静音 {lead:.2f}s  发声 {length:.2f}s  （{cps:.1f} 字/秒）  {ln['text']}")
    (out / "lines_measured.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n已写 {out / 'lines_measured.json'}")


if __name__ == "__main__":
    main()
