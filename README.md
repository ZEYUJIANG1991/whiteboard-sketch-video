# whiteboard-sketch-video

把文章、书籍解读或观点稿，变成「白板手绘动画」短视频的 Agent Skill：

AI 生成 Notion 风白底黑线插画 → 本地引擎**逐笔画出**（笔尖跟随）→ AI 配音 +
词级同步字幕 + BGM → 竖版 1080×1920 成片。

![video frames](examples/video-frames.png)

## 效果示例

| | | |
|---|---|---|
| ![s1](examples/sample-s1.png) | ![s2](examples/sample-s2.png) | ![s4](examples/sample-s4.png) |

## 安装

```bash
npx skills add ZEYUJIANG1991/whiteboard-sketch-video
```

或手动：把 `whiteboard-sketch-video/` 目录拷到你的 Agent skills 目录。

首次使用前：

```bash
bash whiteboard-sketch-video/scripts/setup_env.sh   # 建 Python venv
```

系统依赖：`python3`、`ffmpeg`。配音默认用 MiniMax TTS（可换任何 TTS），
对齐用 whisper 词级时间戳，生图用任何能出 3:4 白底线稿 PNG 的模型。

## 使用

对你的 Agent 说：

> 用白板手绘视频 skill，把这篇文章做成 2 分钟的视频：<文章路径>

或单图模式：

> 把这张图做成白板手绘动画：<图片路径>

## 🎨 品牌定制（换 VI 色 / 换吉祥物 / 换字体）

所有品牌差异都收敛在 `brand/<pack>/` 三个文件里，**管线代码零改动**：

| 文件 | 管什么 | 怎么改 |
|---|---|---|
| `brand.json` | VI 三色 hex、字体路径、画布横竖版、布局、笔尖模式（pen/hand/none） | 机读参数，直接编辑 |
| `character.md` | 主角/吉祥物的生图 prompt 块 | 换成你的 IP 描述（示例见 `brand/examples/mascot-ip-example.md`） |
| `palette.md` | 写进生图提示词的色彩语义 | 换三色与语义，保持"黑主体+白底+彩色只做焦点" |

新品牌 = 复制 `brand/default/` 为 `brand/你的品牌/`，改这三个文件，
项目 `project.json` 里 `"brand": "你的品牌"` 即生效。

默认品牌包是 bcc 创新咨询（蓝 `#0125df` / 青 `#22c1cd` / 粉 `#ff58f9`，
主角为"蓝西装小人"）。

## 工作原理

- **逐笔绘制引擎**（`scripts/wb_engine.py`）：对 AI 生成的 PNG 线稿做骨架化 +
  最近邻笔顺排序，生成 order map 逐像素揭示——黑色线稿先画、彩色填色与批注
  后画（手绘→上色两阶段），无需矢量化（centerline 描摹在笔画交叉处会断线）。
- **合成器**（`scripts/compose.py`）：读 `project.json`（分镜帧表）+
  `brand.json`（品牌参数），逐帧合成幕标题（同样逐笔写出）、插画、字幕、
  笔尖，管道进 ffmpeg。
- **音画同步**：口播稿 → TTS → whisper 词级时间戳 → 强制对齐出字幕与每幕
  起始帧，画面节奏由旁白驱动。

详细流程与踩坑记录见 `whiteboard-sketch-video/references/workflow.md`。

## License

MIT（不含任何字体与手部照片素材；手部指针模式请自备 PNG 并在 brand.json 中指定路径）
