"""火山方舟（Volcengine Ark）接口的公共小工具：读 key、发请求、写日志。只用标准库。"""
import base64
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

ARK_BASE = os.environ.get("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")


def get_key():
    """优先读环境变量 ARK_API_KEY；Windows 下再读用户级环境变量（刚设置、未重启终端时也能读到）。"""
    k = os.environ.get("ARK_API_KEY", "").strip()
    if k:
        return k
    if os.name == "nt":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as h:
                return (winreg.QueryValueEx(h, "ARK_API_KEY")[0] or "").strip()
        except OSError:
            pass
    return ""


def data_uri(path):
    p = Path(path)
    mime = "image/jpeg" if p.suffix.lower() in (".jpg", ".jpeg") else "image/png"
    return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()


def request(method, url, key, payload=None, timeout=240):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Content-Type": "application/json", "Authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:1500]}") from None


def download(url, path, timeout=300):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        Path(path).write_bytes(r.read())


def log(logfile, entry):
    p = Path(logfile)
    p.parent.mkdir(parents=True, exist_ok=True)
    entry = {"time": time.strftime("%Y-%m-%d %H:%M:%S"), **entry}
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_parts(texts, files):
    """把 --prompt 文本和 --prompt-file 文件按顺序拼接，段落之间空一行。"""
    parts = [t.strip() for t in (texts or []) if t.strip()]
    for f in files or []:
        parts.append(Path(f).read_text(encoding="utf-8").strip())
    return "\n\n".join(parts)
