# 九步全流程（含踩坑记录）

目录：1口播稿 → 2TTS → 3对齐 → 4分镜 → 5生图 → 6project.json → 7渲染 → 8验收 → 9发布文案

## 1. 口播稿
口播稿 ≠ 原文。~5 chars/秒（Radio_Host@1.06）；1-3 分钟 = 300-900 字。
每幕一个观点、一个可画的隐喻。开头必须是钩子（场景/反差/数字）。
**术语中文化**：EBITDA→利润 之类，否则 TTS 逐字母念、字幕计长也会出错。
金句密度：每幕至少一句可截图传播的话。存 `script.txt`，每幕一行。

## 2. 配音 TTS
任何能出 mp3 的 TTS 都可以（管线只消费音频文件）。本机若有 `mmtts`（MiniMax）：
```bash
mmtts -f script.txt -o vo.mp3 --voice "Chinese (Mandarin)_Radio_Host" --speed 1.06
```
没有则用你惯用的 TTS API/工具生成 vo.mp3。ffprobe 核对时长，超预期就精简
文稿，别硬塞。TTS 防"卡顿"：中文文稿逗号别太碎——多数 TTS 每个逗号停一拍。

## 3. 词级对齐 → 字幕 + 帧表
需要 whisper 词级时间戳（任选其一安装：Apple Silicon 用 `pip install mlx-whisper`；
其他平台 `pip install openai-whisper` 后命令换成 `whisper`，参数相同）：
```bash
ffmpeg -y -i vo.mp3 -ar 16000 -ac 1 /tmp/vo.wav
mlx_whisper /tmp/vo.wav --language zh --word-timestamps True \
    --condition-on-previous-text False --output-format json --output-dir /tmp
python3 scripts/align_captions.py /tmp/vo.json script.txt --anchors anchors.txt \
    > captions.ts   # stderr 给出 SCENE START FRAMES / TOTAL
```
anchors.txt：第 2..N 幕的幕首词子串，每行一个。
已有现成 SRT 字幕的话可以跳过本步：compose.py 直接接受 .srt（"captions" 指向
srt 文件即可），幕起始帧改为手动按 srt 时间 × fps 计算。
**字幕分句 QA**：切分器已内建视觉宽度计量（拉丁字符按半宽）、《书名》原子化、
短子句防孤字前瞻、无标点长句均衡切分——历史上的"《Rewired》拦腰断""；点子
孤字"两类坑已在源头消除。渲染层另有兜底：超宽字幕按边界自动分割为先后两条
（不缩字号）。发布前仍建议扫一遍 captions.ts（语义级别的怪分句机器测不出）；
手工修法：直接改文本，时间边界按字数比例插值（±0.2s 无感）。

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
start 取自第 3 步帧表；total_frames 取 TOTAL。"captions" 可指向 .ts 或 .srt，
也可整个省略（无字幕）；"brand" 可以是包名（skill 的 brand/ 下）或 brand.json
的绝对路径；"title" 留空则该幕不画标题。

### 单图转换模式（把一张图做成一段白板动画）
一幕、无字幕、无标题即可：
```json
{ "brand": "default", "fps": 30, "total_frames": 240, "tail_frames": 45,
  "out": "out.mp4", "scenes": [ { "start": 0, "image": "your.png" } ] }
```
渲染后用 mux.sh 配任意音频，或直接交付无声片段。

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

## 附：萌系角色的变声配方（猫/吉祥物人设用）

爆款猫号声音密码是"幼态声学"（高基频+高共振峰），甜美女声不够"猫"。
TTS 的 pitch 参数通常保共振峰（越调越像唱高音的大人），"小身体感"要靠
ffmpeg 整体频谱上移：

```bash
# 半音 r=2^(n/12)；⚠ 先 ffprobe 查采样率，asetrate 必须用输入实际采样率
sr=32000; r=$(python3 -c "print(2**(3/12))")
ffmpeg -i vo.mp3 -af "asetrate=${sr}*${r},aresample=${sr},atempo=1/${r},treble=g=2:f=4000" vo_cute.mp3
```

- 机灵科普猫：元气底色 speed 1.1 + 后期 +3 半音（萌但不卡通，长听不腻）
- 奶萌撒娇猫：甜美底色 speed 0.9 + 后期 +4~5 半音（短内容/开头钩子）
- 该处理**逐毫秒保留时长**：字幕对齐与已渲染画面可复用，只需重混音
- mmtts 已支持 --pitch(-12..12)（TTS 内保共振峰的自然升调），但实测带
  pitch 生成会走不同韵律路径、时长大变，慎用；建议 pitch 全放后期
- 口癖锚点：自称"本喵"每期 2-3 次；"喵"只放开场/转折/结尾三处，勿每句用
