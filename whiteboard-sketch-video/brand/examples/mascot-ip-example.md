# 示例：把主角换成吉祥物 IP（自定义品牌包写法）

复制 `brand/default/` 为 `brand/<你的品牌>/`，改三个文件即可，管线代码零改动：

1. **brand.json** — 换 palette 三色 hex、字体路径、ink_hex；竖版/横版改 canvas 与
   title/caption/illustration 的布局数值（横版 1920x1080 参考：title.y=80,
   caption.y=920, illustration.cy=520, max_w=1400, max_h=640）。
2. **character.md** — 重写 Character 块。吉祥物 IP 示例（一只橙色圆猫）：

```text
Character style (IMPORTANT):
Recurring mascot required: 阿橘, a small round cat drawn in the same wobbly
hand-drawn line style, body filled FLAT SOLID orange (#ff7a1a), white belly,
two dot eyes, no mouth unless reacting, tiny legs. 阿橘 must perform the core
conceptual action of the scene, never decorate. Other human figures are
minimalist hollow line-drawn people. Serious and slightly absurd, not cute.
```

   要点：给 IP 起名并在场景 body 里用名字指代；固定 2-3 个不变特征（体色、眼睛、
   体型）保证跨图一致性；IP 是"做事的人"不是贴纸。
3. **palette.md** — 把 Color use 块里的三色与语义换成你的 VI（保持"黑主体+白底+
   彩色只做焦点"的骨架，这是风格成立的前提，别改）。

最后在项目 project.json 里把 "brand" 指向新包名（或 brand.json 的绝对路径）。
