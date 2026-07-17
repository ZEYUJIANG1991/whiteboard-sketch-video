---
name: whiteboard-sketch-video
description: 把文章/书/观点稿变成「白板手绘动画」短视频：AI 生成 Notion 风白底黑线插画（品牌角色+VI 色可插拔），本地引擎逐笔画出，配 AI 配音+词级同步字幕+BGM，输出竖版 1080x1920 成片。Use when user wants 白板手绘视频/whiteboard animation/手绘动画视频/逐笔画出来的视频, to turn an article or book summary into a hand-drawn sketch explainer, or 把图片做成白板动画 (single-image mode). 品牌定制（换 VI 色/吉祥物/字体/横竖版）通过 brand/ 目录的品牌包完成，不改代码。
---

# 白板手绘视频

文章/书 → 分镜口播稿 → AI 配音+词级字幕 → AI 生成白板风插画 → 逐笔绘制引擎 →
竖版成片。视觉体系：纯白底 + 黑色抖动线稿 + 品牌色焦点填色 + 手写批注 + 逐笔
画出（笔尖/手部跟随）。

## 五分钟上手

```bash
bash scripts/setup_env.sh   # 首次：建 .venv（opencv/skimage/scipy/pillow）
```

1. **读品牌包**：`brand/default/`（brand.json 机读参数 + character.md 主角
   prompt 块 + palette.md 色彩语义块）。用户要换品牌时读
   `brand/examples/mascot-ip-example.md` 引导其建新包。
2. **走九步流程**：读 [references/workflow.md](references/workflow.md)
   （口播稿→TTS→对齐→分镜→生图→project.json→渲染→验收→发布文案，含全部坑）。
3. **生图**：读 [references/style-dna.md](references/style-dna.md)（风格铁律）
   和 [references/prompt-template.md](references/prompt-template.md)（模板+QA）。
4. **渲染**：
```bash
.venv/bin/python scripts/compose.py <project.json>      # 全片 silent.mp4
.venv/bin/python scripts/compose.py <project.json> 0    # 单幕预览
bash scripts/mux.sh silent.mp4 vo.mp3 bgm.mp3 final.mp4
```

## 单图转换模式

用户只给一张白底线稿图时：写一个单幕 project.json（title 留空、省略 captions、
total_frames = 时长×fps），compose.py 直接出该图的逐笔绘制片段。模板见
workflow.md 第 6 节。字幕输入支持自研 .ts 或标准 .srt。

## 品牌定制（核心扩展点）

一切品牌差异都在 `brand/<pack>/` 三个文件里，管线代码零改动：
- **brand.json**：VI 三色 hex、字体路径（带 fallback 链）、画布/横竖版、布局
  数值、笔尖模式（pen=极简马克笔 / hand=自备手部 PNG / none）。
- **character.md**：主角/吉祥物的生图 Character 块（默认=bcc 蓝西装小人）。
- **palette.md**：写进提示词的 Color use 块与标注分色口诀。

新品牌 = 复制 default 改这三个文件，project.json 的 "brand" 指向新包名。

## 工程结构

- `scripts/wb_engine.py` — 逐笔引擎：骨架化+最近邻笔顺 → order map 像素揭示；
  黑线稿先画、彩色后画（手绘→上色两阶段）。不要换成 centerline 矢量化（交叉断线）。
- `scripts/compose.py` — 合成器：读 project.json（幕表/帧表）+ brand.json
  （全部品牌参数），出无声片。
- `scripts/align_captions.py` — 正确文稿到 whisper 词级时间的强制对齐
  （ASR 错字不影响时间轴），stderr 输出幕起始帧表。
- `scripts/mux.sh` — 配音+BGM 混音；`scripts/setup_env.sh` — venv。

## 环境依赖

必需：python3、ffmpeg。生图：任何能出 3:4 白底线稿 PNG 的模型（默认 imggen
CLI）。配音：默认 mmtts（MiniMax），可换任何 TTS。对齐：mlx_whisper
（Apple Silicon）或 openai-whisper。缺哪个就提示用户装哪个，不要静默跳过。
