"""生成一套假素材（彩条视频 + 正弦配乐 + 两句"配音"），用来离线试跑 compose.py。不联网、不花钱。

  python examples/make_demo_assets.py
  python scripts/compose.py examples/timeline.example.json
"""
import json
import subprocess
from pathlib import Path

D = Path(__file__).resolve().parent / "demo_assets"
(D / "voice").mkdir(parents=True, exist_ok=True)


def ff(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


for i, src in enumerate(["testsrc2", "smptebars", "mandelbrot"], 1):
    ff("-f", "lavfi", "-i", f"{src}=size=720x1280:rate=24", "-t", "6", "-pix_fmt", "yuv420p", str(D / f"clip{i}.mp4"))
ff("-f", "lavfi", "-i", "sine=frequency=220:duration=20", "-f", "lavfi", "-i", "sine=frequency=330:duration=20",
   "-filter_complex", "amix=inputs=2,volume=0.3", "-ac", "2", str(D / "music.wav"))
measured = []
for vid, freq, lead, length, text in [("01", 600, 0.2, 2.4, "这封信……我到底要不要给他？"),
                                      ("02", 300, 0.2, 1.2, "你在等我吗？")]:
    ff("-f", "lavfi", "-i", f"anullsrc=r=24000:cl=mono", "-f", "lavfi", "-i", f"sine=frequency={freq}",
       "-filter_complex", f"[0]atrim=0:{lead}[a];[1]atrim=0:{length},volume=0.5[b];[a][b]concat=n=2:v=0:a=1",
       str(D / "voice" / f"{vid}.mp3"))
    measured.append({"id": vid, "text": text, "file": f"{vid}.mp3", "lead": lead, "length": length})
(D / "voice" / "lines_measured.json").write_text(json.dumps(measured, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"假素材已生成：{D}")
