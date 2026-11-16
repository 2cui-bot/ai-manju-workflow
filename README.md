# AI 漫剧工作流（ai-manju-workflow）

一套**不限题材**的 AI 漫剧 / AI 短片生产流程：从剧本到成片，包括提示词模板、质量关卡，以及一组可直接运行的 Python + ffmpeg 小工具。

它来自一部 AI 短片从零到成片的真实制作过程：踩过的坑都写进了文档和脚本。文档里标 ✅ 的环节是实测验证过的，标 ⚠️ 的是通用做法，用之前请先小额试一次。

> 示例接口使用火山方舟（Seedream 生图、Seedance 图生视频），配音使用 edge-tts。
> 流程本身与平台无关：换成其他模型，只需改脚本里的请求部分。

---

## 核心思路

1. **先文字、后图片、再视频**：越往后越贵、越难改，所以问题要在前面的环节解决。
2. **一致性靠资产，不靠提示词**：角色、场景、画风先定稿成固定的文字段和参考图，之后每次原样复用。
3. **视频模型只负责"动"**：画面里有什么由首帧/尾帧决定；运动提示词只写怎么动。
4. **尾帧用图生图从首帧改出来**：背景保证一致，视频不会中途跳场。
5. **花钱之前三道关**：自动检查 → 独立审核 → 报价获批；先试一镜，再批量生成。
6. **能剪就不重拍**；必须重拍时，一次只重拍一镜。

## 流程总览

```
A 立项规格 → B 剧本 → C 资产（画风/角色/场景）→ D 分镜 → E 首尾帧 → F 图生视频
→ G 声音（配音/配乐）→ H 合成导出 → I 复盘
```

完整说明见 **[docs/workflow.md](docs/workflow.md)**（含题材调整表：甜宠 / 悬疑 / 古风 / 科幻 / 搞笑 / 动作 / 治愈）。

## 目录

```
docs/workflow.md              完整工作流
templates/prompts.md          提示词模板：画风、角色、场景、首尾帧、图生图改图、降写实、三视图、运动
templates/review_agent_prompt.md  交给另一个 AI 做独立审核的提示词
templates/checklists.md       立项 / 剧本 / 资产 / 每镜 / 每集 / 复盘 检查清单
templates/shot_list.csv       分镜表模板
scripts/                      工具脚本（见下表）
examples/                     示例提示词、配音列表、时间线、离线假素材生成器
```

## 脚本

| 脚本 | 用在哪一步 | 花钱？ | 作用 |
|---|---|---|---|
| `gen_image.py` | E 首尾帧 | 是 | 文生图 / 图生图，提示词按段拼接，支持 `--dry-run` |
| `check_frames.py` | E 检查 | 否 | 首尾帧差异数值、分区报告、叠加图、热力图、手机尺寸图、四角放大 |
| `gen_video.py` | F 视频 | 是 | 首帧（+尾帧）+ 运动提示词 → 视频；先报价，再提交 |
| `contact_sheet.py` | F 审片 | 否 | 带时间戳的帧条 + 自动检测跳场 |
| `analyze_music.py` | G 配乐 | 否 | 响度曲线、强音（候选卡点）、整体响度，切试听片段 |
| `make_voice.py` | G 配音 | 否 | edge-tts 批量配音，测量每句真正的发声起止 |
| `compose.py` | H 合成 | 否 | 按 JSON 时间线一次合成：剪辑、定格、黑场、字幕、配音、配乐自动避让、响度统一、48kHz 导出 |

所有会花钱的脚本都支持 `--dry-run`；输出文件已存在时一律拒绝覆盖，每次请求都写入 `logs/*.jsonl`。

## 快速开始

需要：Python 3.9+、ffmpeg（含 libx264 和 drawtext），以及一个中文字体（Windows 默认用微软雅黑）。

```bash
pip install -r requirements.txt
```

**1. 离线试跑合成（不联网、不花钱）**

```bash
python examples/make_demo_assets.py
python scripts/compose.py examples/timeline.example.json
```

会生成 `examples/demo_out/ep01_demo.mp4`：一段 9:16 竖屏，含三个镜头、字幕、"配音"、配乐避让和片尾黑场。

**2. 看一下生图提示词怎么拼（dry-run 不花钱）**

```bash
python scripts/gen_image.py --prompt-file examples/prompts/shot01_first.txt --prompt-file examples/prompts/char_girl.txt --prompt-file examples/prompts/scene_rooftop.txt --prompt-file examples/prompts/style.txt --prompt-file examples/prompts/no_text.txt --size 720x1280 --out ep01/s01/first.png --dry-run
```

**3. 真正调用接口**：先设置环境变量 `ARK_API_KEY`，再去掉 `--dry-run`。

**4. 检查首尾帧、审片**

```bash
python scripts/check_frames.py ep01/s01/first.png ep01/s01/last.png --out-dir ep01/check/s01
```

```bash
python scripts/contact_sheet.py ep01/clips/s01.mp4 --out ep01/check/s01_sheet.png
```

## 注意事项

- **模型名和价格会变**：脚本里的默认值只是示例，请以平台当前的文档和价目为准（可用 `--model`、`--price`、`--price-per-1k` 修改）。
- **合规**：不用真人脸做角色；不仿制现成 IP 的角色、画风或场景；音乐用公有领域或已获授权的；声音克隆需要本人授权。
- **edge-tts** 依赖微软在线语音服务，可用性和条款以微软为准。
- 不要把 `ARK_API_KEY` 写进任何文件或提交到仓库。

## 许可证

[CC BY 4.0](LICENSE)：可以自由使用、修改、商用，请注明出处（本仓库链接）。
