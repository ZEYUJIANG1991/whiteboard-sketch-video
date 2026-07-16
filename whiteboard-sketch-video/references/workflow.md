# 九步全流程（含踩坑记录）

目录：1口播稿 → 2TTS → 3对齐 → 4分镜 → 5生图 → 6project.json → 7渲染 → 8验收 → 9发布文案

## 1. 口播稿
口播稿 ≠ 原文。~5 chars/秒（Radio_Host@1.06）；1-3 分钟 = 300-900 字。
每幕一个观点、一个可画的隐喻。开头必须是钩子（场景/反差/数字）。
**术语中文化**：EBITDA→利润 之类，否则 TTS 逐字母念、字幕计长也会出错。
金句密度：每幕至少一句可截图传播的话。存 `script.txt`，每幕一行。

## 2. 配音 TTS
```bash
mmtts -f script.txt -o vo.mp3 --voice "Chinese (Mandarin)_Radio_Host" --speed 1.06
```
无 mmtts 时任何能出 mp3 的 TTS 均可（对齐只依赖音频本身）。
ffprobe 核对时长，超预期就精简文稿，别硬塞。

## 3. 词级对齐 → 字幕 + 帧表
```bash
ffmpeg -y -i vo.mp3 -ar 16000 -ac 1 /tmp/vo.wav
mlx_whisper /tmp/vo.wav --language zh --word-timestamps True \
    --condition-on-previous-text False --output-format json --output-dir /tmp
python3 scripts/align_captions.py /tmp/vo.json script.txt --anchors anchors.txt \
    > captions.ts   # stderr 给出 SCENE START FRAMES / TOTAL
```
anchors.txt：第 2..N 幕的幕首词子串，每行一个。
**坑：字幕分句必须逐条人工 QA**——英文词（《Rewired》）按字母计长会拦腰断词
（"里的真/实记录"）；"；"处会把后句头两字孤悬前句尾（"…；点子"）。
修法：直接改 captions.ts 文本，时间边界按字数比例插值（±0.2s 无感）。

## 4. 分镜
用第 3 步帧表定幕数（8-12s/幕体感最好）。每幕：幕标题（≤6 字钩子，不与图内
标签重复）+ 一张插画。取材原则见 style-dna.md。

## 5. 生图
按 prompt-template.md 拼提示词，任何能产"3:4 白底线稿 PNG"的模型都行
（默认 imggen/GPT-Image-2；管线不关心图的来源）。逐张 QA（见模板末尾）。

## 6. project.json
```json
{ "brand": "default", "fps": 30, "total_frames": 3489, "tail_frames": 60,
  "captions": "captions.ts", "out": "silent.mp4",
  "scenes": [ { "start": 0, "title": "麦肯锡 · Rewired", "image": "illust/s1.png" } ] }
```
start 取自第 3 步帧表；total_frames 取 TOTAL。

## 7. 渲染 + 混音
```bash
bash scripts/setup_env.sh                      # 首次
.venv/bin/python scripts/compose.py project.json      # 全片
.venv/bin/python scripts/compose.py project.json 1    # 单幕预览（0起）
bash scripts/mux.sh silent.mp4 vo.mp3 bgm.mp3 final.mp4   # 无BGM传 none
```
BGM 可用 mmmusic 生成（"light minimal acoustic, instrumental, no vocals"）。

## 8. 逐帧验收（不要只看播放器）
每幕抽 起始+1s / 中段 / 收尾 三帧拼图检查：字幕分句、幕标题、绘制顺序
（黑线先、彩色后）、竖版安全区（标题 y≥344、主视觉底 ≤1260、字幕 ≤1360，
6:7 裁剪带 330-1590）。
引擎已内置的坑修：彩色填色紧贴黑轮廓时只吸收浅色 AA 像素（gray>150），
否则素描阶段会出现"无躯干的人"；彩色批注排在黑线稿之后画（先手绘后上色）。

## 9. 发布文案
5 个角度（悬念/金句/清单/POV/故事）+ 金句清单，存 `视频号文案.md`。
钩子首句 ≤20 字，标签 3-5 个。
