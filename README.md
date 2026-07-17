# whiteboard-sketch-video

**把文章、书籍解读或观点稿，变成「白板手绘动画」短视频的 Agent Skill。**

AI 生成 Notion 风白底黑线插画 → 本地引擎**逐笔画出**（笔尖跟随、先线稿后上色）
→ AI 配音 + 词级同步字幕 + BGM → 竖版 1080×1920 成片。

![draw-on demo](examples/demo.gif)

| | | |
|---|---|---|
| ![s1](examples/sample-s1.png) | ![s2](examples/sample-s2.png) | ![s4](examples/sample-s4.png) |

![video frames](examples/video-frames.png)

## 它做什么

对你的 Agent（Claude Code / 任何支持 skills 的 Agent）说一句：

> 用白板手绘视频 skill，把这本书做成 2 分钟的视频：`<文件路径>`

Agent 会自动完成：读素材 → 写口播稿 → TTS 配音 → whisper 词级对齐出字幕和
分镜帧表 → 逐幕生成插画 → 逐笔绘制渲染 → 混音出片。也支持**单图模式**：
"把这张图做成白板动画"。

## 安装

```bash
npx skills add ZEYUJIANG1991/whiteboard-sketch-video
cd <skills目录>/whiteboard-sketch-video && bash scripts/setup_env.sh  # 建 Python venv
```

### 系统依赖
- `python3`（venv 内自动装 opencv/scikit-image/scipy/pillow）
- `ffmpeg`

### ⚠️ 需要自备的两个模型接口

绘制引擎纯本地计算（不花钱），但生图和配音要你自己配 API：

| 环节 | 要求 | 可用选项 |
|---|---|---|
| 生图 | 按提示词出 3:4 白底黑线插画 PNG | GPT-Image / Gemini / 万相 / Seedream 等任意文生图 |
| 配音 | 文本 → mp3 | MiniMax / Azure / 火山 / edge-tts 等任意 TTS |
| 对齐 | whisper 词级时间戳 | `pip install mlx-whisper`（Apple Silicon）或 `openai-whisper` |

把你的 API 用法告诉 Agent 即可——管线只消费 PNG 和 mp3 文件，不关心来源。
生图质量直接决定成片质量，建议选中文书写能力强的模型。已有现成 SRT 字幕的话，
对齐步骤可跳过（compose 直接吃 .srt）。

## 🎨 品牌定制：换 VI 色 / 吉祥物 / 字体 / 横竖版

所有品牌差异收敛在 `brand/<pack>/` 三个文件，**换品牌零代码改动**：

| 文件 | 管什么 |
|---|---|
| `brand.json` | 三色 hex、字体路径（带 fallback 链）、画布尺寸、布局数值、笔尖模式 pen/hand/none |
| `character.md` | 主角/吉祥物的生图 prompt 块（默认：蓝西装小人） |
| `palette.md` | 写进生图提示词的色彩语义 |

新品牌 = 复制 `brand/default/` 改这三个文件，项目里 `"brand": "你的包名"`。
吉祥物 IP 的写法示例见 `brand/examples/mascot-ip-example.md`（含横版布局参数）。
风格骨架（白底/黑线主体/留白/逐笔）在 `references/style-dna.md`，是该风格成立
的前提，不建议改。

## 工作原理

```
文稿 script.txt
   │  TTS（任意）
   ▼
vo.mp3 ──whisper──▶ 词级时间戳 ──align_captions.py──▶ captions.ts + 每幕起始帧
   │                                                        │
   │        提示词模板 + 品牌包 ──任意文生图──▶ illust/*.png  │
   │                                    │                   │
   └────────────────────────────────────┼───────────────────┘
                                        ▼
                              project.json（幕表/帧表/品牌指向）
                                        │
                     scripts/compose.py + wb_engine.py
              （骨架化→笔顺→逐像素揭示；黑线稿先画、彩色后画）
                                        ▼
                            silent.mp4 ──mux.sh──▶ final.mp4
```

- **wb_engine.py**：对 PNG 线稿做骨架化 + 最近邻笔顺排序，生成 order map 逐
  像素揭示。不做矢量化（centerline 描摹在笔画交叉处会断线），直接吃任何
  AI 生成的位图。
- **compose.py**：读 `project.json`（分镜）+ `brand.json`（品牌参数），逐帧
  合成幕标题（同样逐笔写出）、插画、字幕（.ts/.srt，超宽自动缩字）、笔尖，
  管道进 ffmpeg。预览模式输出 `*.previewN.mp4`，不会覆盖正片。
- **音画同步**：画面节奏由旁白的词级时间戳驱动，每一笔都踩在点上。

完整九步流程与踩坑记录：`whiteboard-sketch-video/references/workflow.md`。

## FAQ

**Q: 中文字体哪里来？** brand.json 的 fonts 支持 fallback 链，默认回退到 macOS
系统宋体；想要手写感，把你有版权的手写字体路径填进去（仓库不含字体文件）。

**Q: 大陆网络环境？** setup_env.sh 默认清华 pip 镜像（失败自动回退官方源）；
生图/TTS 选国内可直连的服务即可。

**Q: 想要真人手部跟随？** brand.json `pointer.mode` 设为 `hand` 并自备一张
透明底手持笔 PNG（`hand_asset` 填路径，笔尖朝左上）。默认是极简线稿笔尖。

**Q: 生图偶尔翻车？** 出现纸纹背景/异常大文件（>2MB）直接重生成该张；逐张
QA 清单在 `references/prompt-template.md`。

## License

MIT。不含任何字体与手部照片素材。
