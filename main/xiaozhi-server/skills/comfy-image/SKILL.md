---
name: comfy-image
version: 1.0.0
description: Generate an image with local ComfyUI and show the finished bitmap on the ESP32 OLED display.
metadata:
  xiaozhi:
    functions:
      - generate_comfy_image
---

# Comfy Image

Use this skill when the user asks to generate, draw, create, or make an image/picture/photo, for example:

- `帮我生成一张小猫图片`
- `画一个火箭图片`
- `生成恐龙照片`

Extract the image subject and visual requirements, translate them into English, and call `generate_comfy_image` with an OLED-friendly prompt.

The prompt should describe one centered subject with simple black-and-white line art, bold outlines, high contrast, no text, and no extra objects. For example, if the user asks `帮我画一个太阳`, pass a prompt like `a sun with a round disk and clear rays`.

The tool submits the task to ComfyUI, uses the configured OLED width and height as the target display size, returns whether the task was submitted successfully, and pushes the completed image to the current ESP32 OLED as a 1-bit bitmap.

Do not use shell commands for this skill. Do not tell the user image generation is unsupported before calling the tool.
