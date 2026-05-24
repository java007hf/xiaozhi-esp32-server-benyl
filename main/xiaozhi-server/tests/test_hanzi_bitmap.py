import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from core.providers.tools.server_plugins.plugin_executor import ServerPluginExecutor
from plugins_func.functions.hanzi_bitmap import (
    _extract_character,
    _render_character_bitmap,
    _render_stroke_animation_frames,
)
from plugins_func.register import Action


class FakeWebSocket:
    def __init__(self):
        self.messages = []

    async def send(self, message):
        self.messages.append(message)


class HanziBitmapTests(unittest.TestCase):
    def test_extract_character_from_common_question(self):
        self.assertEqual(_extract_character("永字怎么写？"), "永")
        self.assertEqual(_extract_character("这个字怎么写：璐"), "璐")

    def test_render_character_bitmap_payload_shape(self):
        payload = _render_character_bitmap("A", size=16, config={})

        self.assertEqual(payload["type"], "display_bitmap")
        self.assertEqual(payload["format"], "rows_hex_1bit")
        self.assertEqual(payload["width"], 16)
        self.assertEqual(payload["height"], 16)
        self.assertEqual(payload["duration_ms"], 15000)
        self.assertEqual(len(payload["rows"]), 16)
        self.assertTrue(any(int(row, 16) for row in payload["rows"]))

    def test_render_stroke_animation_frames_for_yong(self):
        frames = _render_stroke_animation_frames("\u6c38", size=16, config={}, frame_interval_ms=0)

        self.assertEqual(len(frames), 5)
        self.assertEqual(frames[-1]["duration_ms"], 15000)
        self.assertEqual(frames[-1]["frame_index"], 5)
        pixel_counts = [
            sum(int(row, 16).bit_count() for row in frame["rows"])
            for frame in frames
        ]
        self.assertEqual(pixel_counts, sorted(pixel_counts))
        self.assertGreater(pixel_counts[-1], pixel_counts[0])

    def test_render_stroke_animation_frames_from_hanzi_writer_data_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            (data_dir / "\u6c34.json").write_text(
                json.dumps(
                    {
                        "medians": [
                            [[512, 900], [512, 500]],
                            [[300, 650], [420, 560]],
                            [[620, 580], [800, 350]],
                            [[500, 500], [350, 260]],
                        ]
                    }
                ),
                encoding="utf-8",
            )
            config = {
                "plugins": {
                    "show_hanzi_stroke_animation": {
                        "hanzi_writer_data_dir": str(data_dir)
                    }
                }
            }

            frames = _render_stroke_animation_frames("\u6c34", size=16, config=config, frame_interval_ms=0)

        self.assertEqual(len(frames), 4)
        self.assertEqual(frames[-1]["frame_count"], 4)
        self.assertTrue(any(int(row, 16) for row in frames[-1]["rows"]))

    def test_executor_awaits_async_bitmap_tool_and_sends_payload(self):
        async def run():
            websocket = FakeWebSocket()
            conn = SimpleNamespace(
                config={
                    "selected_module": {"Intent": "function_call"},
                    "Intent": {"function_call": {"functions": []}},
                },
                session_id="session-1",
                websocket=websocket,
            )
            result = await ServerPluginExecutor(conn).execute(
                conn,
                "show_hanzi_bitmap",
                {"character": "A", "size": 16},
            )
            return result, websocket.messages

        result, messages = asyncio.run(run())

        self.assertEqual(result.action, Action.RESPONSE)
        self.assertEqual(len(messages), 1)
        payload = json.loads(messages[0])
        self.assertEqual(payload["type"], "display_bitmap")
        self.assertEqual(payload["char"], "A")
        self.assertEqual(payload["session_id"], "session-1")

    def test_executor_sends_stroke_animation_frames(self):
        async def run():
            websocket = FakeWebSocket()
            conn = SimpleNamespace(
                config={
                    "selected_module": {"Intent": "function_call"},
                    "Intent": {"function_call": {"functions": []}},
                },
                session_id="session-1",
                websocket=websocket,
            )
            result = await ServerPluginExecutor(conn).execute(
                conn,
                "show_hanzi_stroke_animation",
                {"character": "\u6c38", "size": 16, "frame_interval_ms": 0},
            )
            return result, websocket.messages

        result, messages = asyncio.run(run())

        self.assertEqual(result.action, Action.RESPONSE)
        self.assertEqual(len(messages), 5)
        payload = json.loads(messages[-1])
        self.assertEqual(payload["type"], "display_bitmap")
        self.assertEqual(payload["char"], "\u6c38")
        self.assertEqual(payload["frame_count"], 5)
        self.assertEqual(payload["session_id"], "session-1")


if __name__ == "__main__":
    unittest.main()
