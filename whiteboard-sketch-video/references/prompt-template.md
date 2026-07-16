# 生图提示词模板（每张单独生成，3:4 竖版）

拼装顺序：**风格头 + 场景 body + 品牌包 Character 块 + 品牌包 Color use 块 + 约束尾**。
Character/Color 块从 `brand/<pack>/character.md` 与 `palette.md` 原样取。

## 风格头（固定）
```text
Generate one standalone 3:4 vertical Chinese explanatory illustration,
whiteboard-sketch style.

Visual DNA:
Pure white background. Minimalist black hand-drawn line art. Slightly wobbly
pen lines, like drawn by hand with a fine felt-tip marker on a whiteboard.
Lots of empty white space. Sparse handwritten Chinese annotations in brand
colors. Clean absurd product-sketch feeling. No gradients, no shadows, no
paper texture, no complex background, no commercial vector style, no PPT
infographic look, no cute mascot, no children's illustration.
```

## 场景 body（每幕撰写）
```text
Theme: <一句话主题>

Composition:
<具体画面：主角在哪、做什么核心动作、物件、信息流向；用 THE PROTAGONIST
(<填色描述>) 指代主角>

Chinese handwritten labels:
<标注1> (<primary/secondary/accent 语义色>, 位置) / <标注2> … （≤5 处）
```

## 约束尾（固定）
```text
Constraints:
One image explains only one idea. Keep main subject around 50% of canvas, at
least 35% blank white. At most 4-5 short handwritten Chinese labels, write the
Chinese characters accurately. No title in the top-left corner. Clear but not
instructional, interesting but not childish, strange but clean.
```

## 生成后逐张 QA（必做）
- 翻车信号：文件体积异常大（>2MB）≈ 出了纸纹/照片背景废图 → 直接重生成。
- 检查：白底纯净？黑色主导？填色只有 1-2 处焦点？中文错字？标注是否与
  幕标题重复（幕标题由合成器另画，图内不要有同文案大标题）？
- 幕标题（合成器绘制）与图内标签不得重复——图有大标题时，幕标题改用
  钩子句（"卡在哪里？""第一个关键"）。
