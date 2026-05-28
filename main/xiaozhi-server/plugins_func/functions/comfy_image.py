import asyncio
import copy
import io
import json
import os
import random
import time
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

import requests

from config.config_loader import get_project_dir
from config.logger import setup_logging
from plugins_func.register import Action, ActionResponse, ToolType, register_function

try:
    from PIL import Image, ImageOps
except ImportError:  # pragma: no cover - startup environments should install Pillow
    Image = ImageOps = None

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

TAG = __name__
logger = setup_logging()

DEFAULT_API_URLS = (
    "http://host.docker.internal:8188",
    "http://127.0.0.1:8188",
)
DEFAULT_OLED_WIDTH = 128
DEFAULT_OLED_HEIGHT = 64
DEFAULT_GENERATION_SCALE = 6
DEFAULT_DURATION_MS = 15000
DEFAULT_TIMEOUT_SECONDS = 180
DEFAULT_POLL_INTERVAL_SECONDS = 2
DEFAULT_FILENAME_PREFIX = "xiaozhi_oled"
DEFAULT_PROMPT_TEMPLATE = (
    "simple centered black and white line icon of {prompt}, plain white background, "
    "bold outline, clear silhouette, no text, no extra objects, high contrast, "
    "designed for a {oled_width}x{oled_height} monochrome OLED display"
)
DEFAULT_PROMPT_SUFFIX = ""
DEFAULT_NEGATIVE_PROMPT = (
    "text, letters, watermark, clutter, photo, realistic, gray background, multiple objects, "
    "tiny details, low contrast"
)

_BACKGROUND_TASKS: set[asyncio.Task] = set()


GENERATE_COMFY_IMAGE_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "generate_comfy_image",
        "description": (
            "当用户要求生成、画一张、做一张图片/图像/照片时调用。"
            "请把用户需求改写成英文 OLED 图标提示词：单主体、居中、黑白、高对比、粗轮廓、不要文字。"
            "本工具会向本地 ComfyUI 提交生图任务，并按 OLED 屏幕比例生成；"
            "任务完成后会把生成图转成目标 OLED 宽高的 1-bit 点阵推送到当前 ESP32 OLED 屏幕。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": (
                        "英文图片提示词。需要把中文用户需求翻译并改写成适合 128x64 单色 OLED 的图标式描述，"
                        "例如 simple centered black and white line icon of a sun with rays, bold outline, no text。"
                    ),
                },
                "negative_prompt": {
                    "type": "string",
                    "description": "可选，反向提示词，例如 blurry, low quality。",
                },
                "seed": {
                    "type": "integer",
                    "description": "可选，固定随机种子；不传则自动随机。",
                },
            },
            "required": ["prompt"],
        },
    },
}


def _plugin_config(config: dict | None) -> dict:
    return ((config or {}).get("plugins", {}) or {}).get("generate_comfy_image", {}) or {}


def _normalize_int(value, default: int, minimum: int, maximum: int) -> int:
    try:
        number = int(value if value is not None else default)
    except (TypeError, ValueError):
        number = default
    return max(minimum, min(maximum, number))


def _normalize_seed(seed) -> int:
    if seed is None or seed == "":
        return random.randint(0, 2**63 - 1)
    try:
        return max(0, int(seed))
    except (TypeError, ValueError):
        return random.randint(0, 2**63 - 1)


def _round_up_to_multiple(value: int, multiple: int = 8) -> int:
    if multiple <= 1:
        return int(value)
    return ((int(value) + multiple - 1) // multiple) * multiple


def _generation_size(width: int, height: int, plugin_config: dict | None = None) -> tuple[int, int]:
    plugin_config = plugin_config or {}
    scale = _normalize_int(
        plugin_config.get("generation_scale"), DEFAULT_GENERATION_SCALE, 1, 32
    )
    generation_width = plugin_config.get("generation_width")
    generation_height = plugin_config.get("generation_height")
    if generation_width is None:
        generation_width = width * scale
    if generation_height is None:
        generation_height = height * scale
    return (
        _round_up_to_multiple(_normalize_int(generation_width, width, 8, 4096)),
        _round_up_to_multiple(_normalize_int(generation_height, height, 8, 4096)),
    )


def _format_prompt_template(template: str, prompt: str, width: int, height: int) -> str:
    values = {
        "{prompt}": str(prompt or "").strip(),
        "{oled_width}": str(width),
        "{oled_height}": str(height),
    }
    formatted = str(template or "")
    for key, value in values.items():
        formatted = formatted.replace(key, value)
    return formatted.strip()


def _build_positive_prompt(prompt: str, width: int, height: int, plugin_config: dict | None = None) -> str:
    prompt = str(prompt or "").strip()
    template = str((plugin_config or {}).get("prompt_template") or DEFAULT_PROMPT_TEMPLATE)
    if "{prompt}" in template:
        return _format_prompt_template(template, prompt, width, height)
    return f"{prompt}, {_format_prompt_template(template, prompt, width, height)}"


def _split_urls(value) -> list[str]:
    if not value:
        return []
    if isinstance(value, (list, tuple)):
        raw_urls = value
    else:
        raw_urls = str(value).replace(";", ",").split(",")
    return [str(url).strip().rstrip("/") for url in raw_urls if str(url).strip()]


def _configured_api_urls(config: dict | None) -> list[str]:
    plugin_config = _plugin_config(config)
    urls = []
    urls.extend(_split_urls(os.environ.get("COMFYUI_API_URL")))
    urls.extend(_split_urls(os.environ.get("COMFYUI_BASE_URL")))
    urls.extend(_split_urls(plugin_config.get("api_urls")))
    urls.extend(_split_urls(plugin_config.get("api_url")))
    urls.extend(_split_urls(plugin_config.get("base_url")))
    urls.extend(DEFAULT_API_URLS)

    deduped = []
    seen = set()
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        deduped.append(url)
    return deduped


def _default_workflow_path() -> Path:
    return Path(get_project_dir()) / "skills" / "comfy-image" / "assets" / "local_sd35_turbo_api_prompt.json"


def _load_workflow_template(config: dict | None = None) -> dict:
    plugin_config = _plugin_config(config)
    workflow_path = (
        os.environ.get("COMFYUI_WORKFLOW_PATH")
        or plugin_config.get("workflow_path")
        or _default_workflow_path()
    )
    path = Path(workflow_path)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _linked_node_id(inputs: dict, key: str) -> str | None:
    value = inputs.get(key)
    if isinstance(value, list) and value:
        return str(value[0])
    return None


def _set_clip_text(workflow: dict, node_id: str | None, text: str) -> bool:
    if not node_id or node_id not in workflow:
        return False
    inputs = workflow[node_id].setdefault("inputs", {})
    if "text" not in inputs:
        return False
    inputs["text"] = text
    return True


def _prompt_with_suffix(prompt: str, prompt_suffix: str | None) -> str:
    prompt = str(prompt or "").strip()
    suffix = str(prompt_suffix or "").strip()
    if not suffix:
        return prompt
    if suffix.lower() in prompt.lower():
        return prompt
    return f"{prompt}, {suffix}"


def _prepare_workflow(
    workflow_template: dict,
    prompt: str,
    width: int,
    height: int,
    negative_prompt: str = "",
    seed=None,
    filename_prefix: str = DEFAULT_FILENAME_PREFIX,
    prompt_suffix: str = DEFAULT_PROMPT_SUFFIX,
) -> dict:
    if not str(prompt or "").strip():
        raise ValueError("prompt 不能为空")

    workflow = copy.deepcopy(workflow_template)
    positive_text = _prompt_with_suffix(prompt, prompt_suffix)
    normalized_seed = _normalize_seed(seed)

    clip_nodes = [
        str(node_id)
        for node_id, node in workflow.items()
        if node.get("class_type") == "CLIPTextEncode"
    ]
    positive_id = None
    negative_id = None
    has_size_node = False

    for node_id, node in workflow.items():
        inputs = node.setdefault("inputs", {})
        class_type = str(node.get("class_type") or "")

        if class_type == "KSampler":
            positive_id = positive_id or _linked_node_id(inputs, "positive")
            negative_id = negative_id or _linked_node_id(inputs, "negative")
            if "seed" in inputs:
                inputs["seed"] = normalized_seed

        if "width" in inputs and "height" in inputs:
            inputs["width"] = int(width)
            inputs["height"] = int(height)
            has_size_node = True

        if class_type == "SaveImage" and "filename_prefix" in inputs:
            inputs["filename_prefix"] = filename_prefix

    positive_id = positive_id or (clip_nodes[0] if clip_nodes else None)
    if negative_id is None and len(clip_nodes) > 1:
        negative_id = clip_nodes[1]

    if not _set_clip_text(workflow, positive_id, positive_text):
        raise ValueError("ComfyUI 工作流模板缺少可写入的正向提示词节点")
    _set_clip_text(workflow, negative_id, str(negative_prompt or ""))

    if not has_size_node:
        raise ValueError("ComfyUI 工作流模板缺少 width/height 输入节点")

    return workflow


def _join_url(api_url: str, path: str) -> str:
    return f"{api_url.rstrip('/')}/{path.lstrip('/')}"


def _request_json(method: str, api_url: str, paths: tuple[str, ...], **kwargs) -> dict:
    last_error = None
    for path in paths:
        url = _join_url(api_url, path)
        try:
            response = requests.request(method, url, **kwargs)
            if response.status_code == 404:
                last_error = RuntimeError(f"{url} returned 404")
                continue
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            if getattr(e.response, "status_code", None) == 404:
                last_error = e
                continue
            raise
        except ValueError as e:
            raise RuntimeError(f"{url} did not return JSON") from e
    raise last_error or RuntimeError(f"ComfyUI endpoint not found: {api_url}")


def _request_bytes(method: str, api_url: str, paths: tuple[str, ...], **kwargs) -> bytes:
    last_error = None
    for path in paths:
        url = _join_url(api_url, path)
        try:
            response = requests.request(method, url, **kwargs)
            if response.status_code == 404:
                last_error = RuntimeError(f"{url} returned 404")
                continue
            response.raise_for_status()
            return response.content
        except requests.RequestException as e:
            if getattr(e.response, "status_code", None) == 404:
                last_error = e
                continue
            raise
    raise last_error or RuntimeError(f"ComfyUI endpoint not found: {api_url}")


def _submit_prompt(api_url: str, workflow: dict) -> str:
    data = _request_json(
        "POST",
        api_url,
        ("prompt", "api/prompt"),
        json={"prompt": workflow, "client_id": str(uuid.uuid4())},
        timeout=15,
    )
    prompt_id = data.get("prompt_id")
    if not prompt_id:
        raise RuntimeError(f"ComfyUI submit response missing prompt_id: {data}")
    return str(prompt_id)


def _submit_to_any_url(api_urls: list[str], workflow: dict) -> tuple[str, str]:
    errors = []
    for api_url in api_urls:
        try:
            prompt_id = _submit_prompt(api_url, workflow)
            return api_url, prompt_id
        except Exception as e:
            errors.append(f"{api_url}: {e}")
            logger.bind(tag=TAG).warning(f"ComfyUI submit failed via {api_url}: {e}")
    raise RuntimeError("无法连接或提交到 ComfyUI: " + " | ".join(errors))


def _submit_generation(config: dict | None, prompt: str, negative_prompt: str = "", seed=None) -> dict:
    plugin_config = _plugin_config(config)
    width = _normalize_int(plugin_config.get("oled_width"), DEFAULT_OLED_WIDTH, 8, 2048)
    height = _normalize_int(plugin_config.get("oled_height"), DEFAULT_OLED_HEIGHT, 8, 2048)
    generation_width, generation_height = _generation_size(width, height, plugin_config)
    duration_ms = _normalize_int(plugin_config.get("duration_ms"), DEFAULT_DURATION_MS, 1000, 300000)
    timeout_seconds = _normalize_int(
        plugin_config.get("timeout_seconds"), DEFAULT_TIMEOUT_SECONDS, 10, 3600
    )
    poll_interval_seconds = _normalize_int(
        plugin_config.get("poll_interval_seconds"), DEFAULT_POLL_INTERVAL_SECONDS, 1, 60
    )
    filename_prefix = str(plugin_config.get("filename_prefix") or DEFAULT_FILENAME_PREFIX)
    prompt_suffix = str(plugin_config.get("prompt_suffix") or DEFAULT_PROMPT_SUFFIX)
    configured_negative = plugin_config.get("negative_prompt", DEFAULT_NEGATIVE_PROMPT)
    final_negative = negative_prompt if negative_prompt else configured_negative
    positive_prompt = _build_positive_prompt(prompt, width, height, plugin_config)

    workflow = _prepare_workflow(
        _load_workflow_template(config),
        prompt=positive_prompt,
        width=generation_width,
        height=generation_height,
        negative_prompt=final_negative,
        seed=seed,
        filename_prefix=filename_prefix,
        prompt_suffix=prompt_suffix,
    )
    api_url, prompt_id = _submit_to_any_url(_configured_api_urls(config), workflow)
    return {
        "api_url": api_url,
        "prompt_id": prompt_id,
        "width": width,
        "height": height,
        "generation_width": generation_width,
        "generation_height": generation_height,
        "duration_ms": duration_ms,
        "timeout_seconds": timeout_seconds,
        "poll_interval_seconds": poll_interval_seconds,
    }


def _history_entry(history: dict, prompt_id: str) -> dict | None:
    if not isinstance(history, dict):
        return None
    entry = history.get(prompt_id)
    if isinstance(entry, dict):
        return entry
    if "outputs" in history:
        return history
    return None


def _select_output_image(history: dict, prompt_id: str) -> dict | None:
    entry = _history_entry(history, prompt_id)
    if not entry:
        return None
    outputs = entry.get("outputs") or {}
    for output in outputs.values():
        for image in output.get("images") or []:
            if image.get("filename"):
                return image
    return None


def _history_error(history: dict, prompt_id: str) -> str | None:
    entry = _history_entry(history, prompt_id)
    if not entry:
        return None
    status = entry.get("status") or {}
    status_str = str(status.get("status_str") or "").lower()
    if status_str in {"error", "failed"}:
        return status_str
    for message in status.get("messages") or []:
        if isinstance(message, (list, tuple)) and message and message[0] == "execution_error":
            return "execution_error"
    return None


def _history_completed(history: dict, prompt_id: str) -> bool:
    entry = _history_entry(history, prompt_id)
    if not entry:
        return False
    status = entry.get("status") or {}
    return bool(status.get("completed"))


def _get_history(api_url: str, prompt_id: str) -> dict:
    return _request_json(
        "GET",
        api_url,
        (f"history/{prompt_id}", f"api/history/{prompt_id}"),
        timeout=15,
    )


def _wait_for_output_image(
    api_url: str,
    prompt_id: str,
    timeout_seconds: int,
    poll_interval_seconds: int,
) -> dict:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        history = _get_history(api_url, prompt_id)
        image = _select_output_image(history, prompt_id)
        if image:
            return image
        error = _history_error(history, prompt_id)
        if error:
            raise RuntimeError(f"ComfyUI 生成失败: {error}")
        if _history_completed(history, prompt_id):
            raise RuntimeError("ComfyUI 任务完成但没有输出图片")
        time.sleep(poll_interval_seconds)
    raise TimeoutError(f"ComfyUI 生图超时: {timeout_seconds}s")


def _download_image(api_url: str, image_ref: dict) -> bytes:
    params = {
        "filename": image_ref.get("filename"),
        "type": image_ref.get("type") or "output",
    }
    subfolder = image_ref.get("subfolder")
    if subfolder:
        params["subfolder"] = subfolder
    return _request_bytes(
        "GET",
        api_url,
        ("view", "api/view"),
        params=params,
        timeout=30,
    )


def _image_to_rows_hex(image, width: int, height: int, auto_invert: bool = True) -> list[str]:
    if Image is None or ImageOps is None:
        raise RuntimeError("Pillow 未安装，无法转换 OLED 点阵图")

    resampling = getattr(Image, "Resampling", Image).LANCZOS
    fitted = ImageOps.fit(image.convert("RGB"), (width, height), method=resampling)
    gray = ImageOps.autocontrast(fitted.convert("L"))
    dither = getattr(getattr(Image, "Dither", Image), "FLOYDSTEINBERG", 3)
    mono = gray.convert("1", dither=dither)

    pixels = []
    lit_count = 0
    for y in range(height):
        row = []
        for x in range(width):
            on = mono.getpixel((x, y)) != 0
            row.append(on)
            if on:
                lit_count += 1
        pixels.append(row)

    invert = auto_invert and lit_count > (width * height * 0.55)
    hex_width = (width + 3) // 4
    rows = []
    for y in range(height):
        row_value = 0
        for x in range(width):
            on = pixels[y][x]
            if invert:
                on = not on
            if on:
                row_value |= 1 << (width - 1 - x)
        rows.append(f"{row_value:0{hex_width}x}")
    return rows


def _build_bitmap_payload(
    image_bytes: bytes,
    prompt: str,
    width: int,
    height: int,
    duration_ms: int,
    session_id: str | None = None,
) -> dict:
    image = Image.open(io.BytesIO(image_bytes))
    payload = {
        "type": "display_bitmap",
        "format": "rows_hex_1bit",
        "title": "COMFY",
        "prompt": str(prompt or "")[:80],
        "width": width,
        "height": height,
        "duration_ms": duration_ms,
        "rows": _image_to_rows_hex(image, width, height),
        "source": "comfyui",
    }
    if session_id:
        payload["session_id"] = session_id
    return payload


async def _poll_and_push(
    websocket,
    session_id: str | None,
    api_url: str,
    prompt_id: str,
    prompt: str,
    width: int,
    height: int,
    duration_ms: int,
    timeout_seconds: int,
    poll_interval_seconds: int,
):
    try:
        image_ref = await asyncio.to_thread(
            _wait_for_output_image,
            api_url,
            prompt_id,
            timeout_seconds,
            poll_interval_seconds,
        )
        image_bytes = await asyncio.to_thread(_download_image, api_url, image_ref)
        payload = await asyncio.to_thread(
            _build_bitmap_payload,
            image_bytes,
            prompt,
            width,
            height,
            duration_ms,
            session_id,
        )
        await websocket.send(json.dumps(payload, ensure_ascii=False))
        logger.bind(tag=TAG).info(f"ComfyUI image pushed to ESP32: prompt_id={prompt_id}")
    except Exception as e:
        logger.bind(tag=TAG).error(f"ComfyUI image background task failed: {e}")


def _schedule_background(coro):
    task = asyncio.create_task(coro)
    _BACKGROUND_TASKS.add(task)
    task.add_done_callback(_BACKGROUND_TASKS.discard)
    return task


@register_function("generate_comfy_image", GENERATE_COMFY_IMAGE_FUNCTION_DESC, ToolType.SYSTEM_CTL)
async def generate_comfy_image(
    conn: "ConnectionHandler",
    prompt: str,
    negative_prompt: str = "",
    seed=None,
):
    try:
        websocket = getattr(conn, "websocket", None)
        if websocket is None:
            return ActionResponse(Action.ERROR, response="当前连接没有可用的 ESP32 websocket")

        submit_result = await asyncio.to_thread(
            _submit_generation,
            getattr(conn, "config", {}),
            prompt,
            negative_prompt,
            seed,
        )
        session_id = getattr(conn, "session_id", None)
        _schedule_background(
            _poll_and_push(
                websocket,
                session_id,
                submit_result["api_url"],
                submit_result["prompt_id"],
                prompt,
                submit_result["width"],
                submit_result["height"],
                submit_result["duration_ms"],
                submit_result["timeout_seconds"],
                submit_result["poll_interval_seconds"],
            )
        )

        response = (
            f"生图任务已提交，会输出为 OLED 尺寸 {submit_result['width']}x{submit_result['height']}，"
            "完成后会显示在屏幕上。"
        )
        return ActionResponse(Action.RESPONSE, result=response, response=response)
    except Exception as e:
        logger.bind(tag=TAG).error(f"ComfyUI image submit failed: {e}")
        return ActionResponse(Action.ERROR, response=f"提交 ComfyUI 生图任务失败: {e}")
