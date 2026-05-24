---
name: hanzi-bitmap
version: 1.0.0
description: Show a Chinese character as a dot-matrix bitmap or stroke-order animation on the ESP32 OLED display.
metadata:
  xiaozhi:
    functions:
      - show_hanzi_bitmap
      - show_hanzi_stroke_animation
---

# Hanzi Bitmap

Use this skill when the user asks how a single character is written, for example:

- `永字怎么写`
- `这个字怎么写：永`
- `把永的点阵图发给屏幕`
- `显示永字点阵`

Extract exactly one target character from the request and call `show_hanzi_bitmap`.

When the user asks for strokes, stroke order, or says to show the character one stroke at a time, call `show_hanzi_stroke_animation` instead. Examples:

- `永远的永笔画是这样的`
- `永字的笔顺怎么写`
- `一笔一划显示永`

If the user provides more than one character and does not clearly identify the target, ask which one to show. Do not use shell commands for this skill.

Stroke animation data is loaded from `assets/strokes.json` first, then from the optional `hanzi-writer-data` package when available. If a requested character has no stroke data, report that the stroke animation data is not available for that character yet.
