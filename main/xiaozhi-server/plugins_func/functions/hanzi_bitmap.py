import json
import os
import re
import asyncio
import unicodedata
from pathlib import Path
from typing import TYPE_CHECKING

from config.config_loader import get_project_dir
from config.logger import setup_logging
from plugins_func.register import register_function, ToolType, ActionResponse, Action

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover - startup environments should install Pillow
    Image = ImageDraw = ImageFont = None

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

TAG = __name__
logger = setup_logging()

DEFAULT_BITMAP_SIZE = 64
MIN_BITMAP_SIZE = 16
MAX_BITMAP_SIZE = 64
DEFAULT_FRAME_INTERVAL_MS = 900
DEFAULT_FINAL_STROKE_DURATION_MS = 15000


SHOW_HANZI_BITMAP_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "show_hanzi_bitmap",
        "description": (
            "当用户问某个字怎么写、要求显示某个汉字/字符的写法或点阵时调用。"
            "本工具会把单个字符渲染成 1-bit 点阵，并发送给当前 ESP32 OLED 屏显示。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "character": {
                    "type": "string",
                    "description": "要显示的单个字或字符，例如“永”。如果用户说“永字怎么写”，传“永”。",
                },
                "size": {
                    "type": "integer",
                    "description": "可选点阵尺寸，范围 16 到 64，默认 64。",
                },
            },
            "required": ["character"],
        },
    },
}

SHOW_HANZI_STROKE_ANIMATION_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "show_hanzi_stroke_animation",
        "description": (
            "当用户询问某个字的笔画、笔顺，或要求一笔一划展示某个字怎么写时调用。"
            "本工具会按笔画顺序生成点阵动画帧，并连续发送给当前 ESP32 OLED 屏显示。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "character": {
                    "type": "string",
                    "description": "要展示笔画动画的单个字，例如用户说“永远的永笔画是这样的”时传“永”。",
                },
                "size": {
                    "type": "integer",
                    "description": "可选点阵尺寸，范围 16 到 64，默认 64。",
                },
                "frame_interval_ms": {
                    "type": "integer",
                    "description": "可选，每一笔之间的间隔毫秒数，默认 900。",
                },
            },
            "required": ["character"],
        },
    },
}


def _extract_character(text: str) -> str:
    value = str(text or "").strip()
    value = value.strip("\"'`“”‘’")
    if ":" in value or "：" in value:
        tail = re.split(r"[:：]", value)[-1].strip()
        if tail:
            value = tail
    value = re.sub(r"(这个|那個|那个)?字(怎么写|怎麼寫|如何写|如何寫)?[？?。.!！]*$", "", value)
    value = re.sub(r"(怎么写|怎麼寫|如何写|如何寫)[？?。.!！]*$", "", value)
    value = value.strip("\"'`“”‘’ \t\r\n:：,，。.!！?？")

    candidates = []
    for ch in value:
        if ch.isspace():
            continue
        if unicodedata.category(ch).startswith("P"):
            continue
        candidates.append(ch)

    if not candidates:
        raise ValueError("character 不能为空")

    for ch in candidates:
        if "\u4e00" <= ch <= "\u9fff":
            return ch
    return candidates[0]


def _normalize_size(size) -> int:
    try:
        normalized = int(size or DEFAULT_BITMAP_SIZE)
    except (TypeError, ValueError):
        normalized = DEFAULT_BITMAP_SIZE
    return max(MIN_BITMAP_SIZE, min(MAX_BITMAP_SIZE, normalized))


def _normalize_frame_interval_ms(frame_interval_ms) -> int:
    try:
        normalized = int(frame_interval_ms if frame_interval_ms is not None else DEFAULT_FRAME_INTERVAL_MS)
    except (TypeError, ValueError):
        normalized = DEFAULT_FRAME_INTERVAL_MS
    return max(0, min(5000, normalized))


def _font_candidates(config: dict) -> list[str]:
    plugin_config = (config or {}).get("plugins", {}).get("show_hanzi_bitmap", {}) or {}
    candidates = [
        plugin_config.get("font_path"),
        os.environ.get("HANZI_BITMAP_FONT_PATH"),
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simsun.ttc",
        r"C:\Windows\Fonts\simkai.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/arphic/ukai.ttc",
        "/usr/share/fonts/truetype/arphic/uming.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    return [str(path) for path in candidates if path and Path(str(path)).exists()]


def _load_font(character: str, size: int, config: dict):
    if ImageFont is None:
        raise RuntimeError("Pillow 未安装，无法生成点阵图")

    last_error = None
    for font_path in _font_candidates(config):
        try:
            return ImageFont.truetype(font_path, size), font_path
        except Exception as e:
            last_error = e
            logger.bind(tag=TAG).warning(f"加载字体失败 {font_path}: {e}")

    try:
        return ImageFont.load_default(size=size), "Pillow default"
    except TypeError:
        if last_error:
            logger.bind(tag=TAG).warning(f"使用默认字体，上一字体错误: {last_error}")
        return ImageFont.load_default(), "Pillow default"


def _image_to_rows(image, size: int) -> list[str]:
    threshold = 64
    hex_width = (size + 3) // 4
    rows = []
    for row_index in range(size):
        row_value = 0
        for col_index in range(size):
            if image.getpixel((col_index, row_index)) > threshold:
                row_value |= 1 << (size - 1 - col_index)
        rows.append(f"{row_value:0{hex_width}x}")
    return rows


def _stroke_data_paths(config: dict | None = None) -> list[Path]:
    plugin_config = (config or {}).get("plugins", {}).get("show_hanzi_stroke_animation", {}) or {}
    candidates = [
        plugin_config.get("stroke_data_path"),
        Path(get_project_dir()) / "skills" / "hanzi-bitmap" / "assets" / "strokes.json",
    ]
    return [Path(path) for path in candidates if path and Path(path).exists()]


def _load_stroke_data(config: dict | None = None) -> dict:
    merged = {}
    for path in _stroke_data_paths(config):
        with open(path, "r", encoding="utf-8") as f:
            merged.update(json.load(f))
    return merged


def _hanzi_writer_data_dirs(config: dict | None = None) -> list[Path]:
    plugin_config = (config or {}).get("plugins", {}).get("show_hanzi_stroke_animation", {}) or {}
    candidates = [
        plugin_config.get("hanzi_writer_data_dir"),
        os.environ.get("HANZI_WRITER_DATA_DIR"),
        Path(get_project_dir()) / "node_modules" / "hanzi-writer-data",
        Path("/usr/local/lib/node_modules/hanzi-writer-data"),
    ]
    return [Path(path) for path in candidates if path and Path(path).is_dir()]


def _load_hanzi_writer_entry(character: str, config: dict | None = None) -> dict | None:
    filename = f"{character}.json"
    for data_dir in _hanzi_writer_data_dirs(config):
        path = data_dir / filename
        if not path.exists():
            continue
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def _convert_hanzi_writer_medians(medians: list) -> list[list[list[float]]]:
    strokes = []
    for median in medians:
        points = []
        for point in median:
            if len(point) < 2:
                continue
            x = max(0.0, min(32.0, float(point[0]) * 32.0 / 1024.0))
            y = max(0.0, min(32.0, (1024.0 - float(point[1])) * 32.0 / 1024.0))
            points.append([x, y])
        if points:
            strokes.append(points)
    return strokes


def _load_stroke_entry(character: str, config: dict | None = None) -> dict | None:
    local_data = _load_stroke_data(config)
    if character in local_data:
        return local_data[character]

    hanzi_writer_entry = _load_hanzi_writer_entry(character, config)
    if hanzi_writer_entry and hanzi_writer_entry.get("medians"):
        return {
            "stroke_width": 2,
            "strokes": _convert_hanzi_writer_medians(hanzi_writer_entry["medians"]),
            "source": "hanzi-writer-data",
        }

    return None


def _scaled_points(points: list[list[float]], size: int) -> list[tuple[int, int]]:
    scale = size / 32.0
    return [
        (
            max(0, min(size - 1, int(round(point[0] * scale)))),
            max(0, min(size - 1, int(round(point[1] * scale)))),
        )
        for point in points
    ]


def _draw_stroke(draw, points: list[tuple[int, int]], width: int):
    if not points:
        return
    if len(points) == 1:
        x, y = points[0]
        radius = max(1, width)
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=255)
        return

    draw.line(points, fill=255, width=width, joint="curve")
    radius = max(1, width // 2)
    for x, y in points:
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=255)


def _render_stroke_animation_frames(
    character: str,
    size: int = DEFAULT_BITMAP_SIZE,
    config: dict | None = None,
    frame_interval_ms: int = DEFAULT_FRAME_INTERVAL_MS,
    final_duration_ms: int = DEFAULT_FINAL_STROKE_DURATION_MS,
) -> list[dict]:
    if Image is None or ImageDraw is None:
        raise RuntimeError("Pillow 未安装，无法生成点阵动画")

    size = _normalize_size(size)
    entry = _load_stroke_entry(character, config)
    if not entry:
        raise ValueError(f"暂时没有“{character}”的笔画数据")

    strokes = entry.get("strokes") or []
    if not strokes:
        raise ValueError(f"“{character}”的笔画数据为空")

    stroke_width = max(1, int(round(float(entry.get("stroke_width", 2)) * size / 32.0)))
    interval = _normalize_frame_interval_ms(frame_interval_ms)
    intermediate_duration_ms = max(1000, interval + 300)
    canvas = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(canvas)
    frames = []

    for index, stroke in enumerate(strokes, start=1):
        points = _scaled_points(stroke, size)
        _draw_stroke(draw, points, stroke_width)
        is_final = index == len(strokes)
        frames.append(
            {
                "type": "display_bitmap",
                "format": "rows_hex_1bit",
                "title": f"{character} {index}/{len(strokes)}",
                "char": character,
                "width": size,
                "height": size,
                "duration_ms": final_duration_ms if is_final else intermediate_duration_ms,
                "rows": _image_to_rows(canvas, size),
                "frame_index": index,
                "frame_count": len(strokes),
            }
        )

    return frames


def _render_character_bitmap(character: str, size: int = DEFAULT_BITMAP_SIZE, config: dict | None = None):
    if Image is None or ImageDraw is None:
        raise RuntimeError("Pillow 未安装，无法生成点阵图")

    size = _normalize_size(size)
    canvas = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(canvas)

    font = None
    font_source = ""
    margin = 1
    for font_size in range(size, 7, -1):
        font, font_source = _load_font(character, font_size, config or {})
        bbox = draw.textbbox((0, 0), character, font=font)
        glyph_width = bbox[2] - bbox[0]
        glyph_height = bbox[3] - bbox[1]
        if glyph_width <= size - margin * 2 and glyph_height <= size - margin * 2:
            break

    bbox = draw.textbbox((0, 0), character, font=font)
    glyph_width = bbox[2] - bbox[0]
    glyph_height = bbox[3] - bbox[1]
    x = (size - glyph_width) // 2 - bbox[0]
    y = (size - glyph_height) // 2 - bbox[1]
    draw.text((x, y), character, fill=255, font=font)

    return {
        "type": "display_bitmap",
        "format": "rows_hex_1bit",
        "title": "HANZI",
        "char": character,
        "width": size,
        "height": size,
        "duration_ms": 15000,
        "rows": _image_to_rows(canvas, size),
        "font": font_source,
    }


@register_function("show_hanzi_bitmap", SHOW_HANZI_BITMAP_FUNCTION_DESC, ToolType.SYSTEM_CTL)
async def show_hanzi_bitmap(
    conn: "ConnectionHandler",
    character: str,
    size: int = DEFAULT_BITMAP_SIZE,
):
    try:
        char = _extract_character(character)
        payload = _render_character_bitmap(char, size=size, config=getattr(conn, "config", {}))
        session_id = getattr(conn, "session_id", None)
        if session_id:
            payload["session_id"] = session_id

        websocket = getattr(conn, "websocket", None)
        if websocket is None:
            return ActionResponse(Action.ERROR, response="当前连接没有可用的 ESP32 websocket")

        await websocket.send(json.dumps(payload, ensure_ascii=False))
        response = f"已把“{char}”的点阵图发到屏幕上。"
        return ActionResponse(Action.RESPONSE, result=response, response=response)
    except Exception as e:
        logger.bind(tag=TAG).error(f"发送汉字点阵失败: {e}")
        return ActionResponse(Action.ERROR, response=f"发送汉字点阵失败: {e}")


@register_function("show_hanzi_stroke_animation", SHOW_HANZI_STROKE_ANIMATION_FUNCTION_DESC, ToolType.SYSTEM_CTL)
async def show_hanzi_stroke_animation(
    conn: "ConnectionHandler",
    character: str,
    size: int = DEFAULT_BITMAP_SIZE,
    frame_interval_ms: int = DEFAULT_FRAME_INTERVAL_MS,
):
    try:
        char = _extract_character(character)
        interval = _normalize_frame_interval_ms(frame_interval_ms)
        frames = _render_stroke_animation_frames(
            char,
            size=size,
            config=getattr(conn, "config", {}),
            frame_interval_ms=interval,
        )
        websocket = getattr(conn, "websocket", None)
        if websocket is None:
            return ActionResponse(Action.ERROR, response="当前连接没有可用的 ESP32 websocket")

        session_id = getattr(conn, "session_id", None)
        for index, payload in enumerate(frames):
            if session_id:
                payload["session_id"] = session_id
            await websocket.send(json.dumps(payload, ensure_ascii=False))
            if index < len(frames) - 1 and interval > 0:
                await asyncio.sleep(interval / 1000)

        response = f"已把“{char}”的笔画动画发到屏幕上。"
        return ActionResponse(Action.RESPONSE, result=response, response=response)
    except Exception as e:
        logger.bind(tag=TAG).error(f"发送汉字笔画动画失败: {e}")
        return ActionResponse(Action.ERROR, response=f"发送汉字笔画动画失败: {e}")
