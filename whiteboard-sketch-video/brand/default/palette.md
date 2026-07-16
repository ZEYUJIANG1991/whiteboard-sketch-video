# 色彩语义：写进生图提示词的 Color use 块

每张插画提示词末尾嵌入（hex 与 brand.json 的 palette 保持一致）：

```text
Color use (brand palette, use EXACTLY these colors and no others):
- Black ink: all main line art and outlines. Black stays the DOMINANT color.
- Deep cobalt blue #0125df: the protagonist's suit fill; main flow arrows;
  primary handwritten labels.
- Bright teal #22c1cd: ONE secondary key-object flat fill; secondary notes.
- Vivid magenta pink #ff58f9: warnings / problems / key results — at most
  1-2 spots.
Colored flat fills are limited to 1-2 focal elements total (protagonist suit
+ at most one key object). Everything else stays hollow. Flat fills only,
no shading. Background stays pure white.
```

标注分色口诀：**蓝=主线，青=辅注，粉=扎心**。每图手写中文标注 ≤5 处、每处 2-8 字。
