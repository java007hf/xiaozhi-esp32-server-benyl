import asyncio
import unittest
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image, ImageDraw

from core.providers.tools.server_plugins.plugin_executor import ServerPluginExecutor
from plugins_func.functions.comfy_image import (
    _build_bitmap_payload,
    _build_positive_prompt,
    _generation_size,
    _image_to_rows_hex,
    _prepare_workflow,
    _select_output_image,
    generate_comfy_image,
)
from plugins_func.register import Action


class ComfyImageTests(unittest.TestCase):
    def workflow_template(self):
        return {
            "3": {
                "class_type": "CLIPTextEncode",
                "inputs": {"clip": ["2", 0], "text": "old positive"},
            },
            "4": {
                "class_type": "CLIPTextEncode",
                "inputs": {"clip": ["2", 0], "text": "old negative"},
            },
            "5": {
                "class_type": "EmptySD3LatentImage",
                "inputs": {"width": 768, "height": 768, "batch_size": 1},
            },
            "6": {
                "class_type": "KSampler",
                "inputs": {
                    "positive": ["3", 0],
                    "negative": ["4", 0],
                    "latent_image": ["5", 0],
                    "seed": 12345,
                },
            },
            "8": {
                "class_type": "SaveImage",
                "inputs": {"images": ["7", 0], "filename_prefix": "old_prefix"},
            },
        }

    def test_prepare_workflow_sets_prompt_size_seed_and_prefix(self):
        template = self.workflow_template()

        workflow = _prepare_workflow(
            template,
            prompt="a tiny rocket",
            width=128,
            height=64,
            negative_prompt="blurry",
            seed=42,
            filename_prefix="unit_oled",
            prompt_suffix="high contrast",
        )

        self.assertEqual(template["5"]["inputs"]["width"], 768)
        self.assertIn("a tiny rocket", workflow["3"]["inputs"]["text"])
        self.assertIn("high contrast", workflow["3"]["inputs"]["text"])
        self.assertEqual(workflow["4"]["inputs"]["text"], "blurry")
        self.assertEqual(workflow["5"]["inputs"]["width"], 128)
        self.assertEqual(workflow["5"]["inputs"]["height"], 64)
        self.assertEqual(workflow["6"]["inputs"]["seed"], 42)
        self.assertEqual(workflow["8"]["inputs"]["filename_prefix"], "unit_oled")

    def test_generation_size_scales_oled_aspect_ratio(self):
        self.assertEqual(_generation_size(128, 64, {}), (768, 384))
        self.assertEqual(
            _generation_size(128, 64, {"generation_scale": 4}),
            (512, 256),
        )

    def test_positive_prompt_wraps_user_subject_for_oled(self):
        prompt = _build_positive_prompt("a sun with rays", 128, 64, {})

        self.assertIn("a sun with rays", prompt)
        self.assertIn("128x64", prompt)
        self.assertIn("black and white", prompt)
        self.assertIn("no text", prompt)

    def test_image_to_rows_hex_uses_rectangular_oled_shape(self):
        image = Image.new("L", (128, 64), 0)
        draw = ImageDraw.Draw(image)
        draw.rectangle((16, 8, 111, 55), fill=255)

        rows = _image_to_rows_hex(image, 128, 64, auto_invert=False)

        self.assertEqual(len(rows), 64)
        self.assertTrue(all(len(row) == 32 for row in rows))
        self.assertTrue(any(int(row, 16) for row in rows))

    def test_build_bitmap_payload_from_generated_image(self):
        image = Image.new("RGB", (128, 64), "black")
        draw = ImageDraw.Draw(image)
        draw.ellipse((36, 8, 92, 56), fill="white")
        buffer = BytesIO()
        image.save(buffer, format="PNG")

        payload = _build_bitmap_payload(
            buffer.getvalue(),
            prompt="white circle",
            width=128,
            height=64,
            duration_ms=15000,
            session_id="session-1",
        )

        self.assertEqual(payload["type"], "display_bitmap")
        self.assertEqual(payload["format"], "rows_hex_1bit")
        self.assertEqual(payload["width"], 128)
        self.assertEqual(payload["height"], 64)
        self.assertEqual(payload["duration_ms"], 15000)
        self.assertEqual(payload["session_id"], "session-1")
        self.assertEqual(len(payload["rows"]), 64)

    def test_select_output_image_from_comfy_history(self):
        history = {
            "prompt-1": {
                "outputs": {
                    "8": {
                        "images": [
                            {
                                "filename": "xiaozhi_oled_00001_.png",
                                "subfolder": "",
                                "type": "output",
                            }
                        ]
                    }
                }
            }
        }

        image_ref = _select_output_image(history, "prompt-1")

        self.assertEqual(image_ref["filename"], "xiaozhi_oled_00001_.png")
        self.assertEqual(image_ref["type"], "output")

    def test_skill_exposes_generate_comfy_image_tool(self):
        conn = SimpleNamespace(
            config={
                "selected_module": {"Intent": "function_call"},
                "Intent": {"function_call": {"functions": []}},
                "skills": {"paths": ["skills"]},
            }
        )

        tools = ServerPluginExecutor(conn).get_tools()

        self.assertIn("generate_comfy_image", tools)

    def test_generate_comfy_image_submits_and_schedules_background_task(self):
        async def run():
            scheduled = []

            def fake_schedule(coro):
                scheduled.append(coro)
                coro.close()

            conn = SimpleNamespace(
                config={},
                session_id="session-1",
                websocket=SimpleNamespace(send=lambda message: None),
            )
            submit_result = {
                "api_url": "http://comfy",
                "prompt_id": "prompt-1",
                "width": 128,
                "height": 64,
                "duration_ms": 15000,
                "timeout_seconds": 180,
                "poll_interval_seconds": 2,
            }
            with patch(
                "plugins_func.functions.comfy_image._submit_generation",
                return_value=submit_result,
            ), patch(
                "plugins_func.functions.comfy_image._schedule_background",
                side_effect=fake_schedule,
            ):
                result = await generate_comfy_image(conn, "a cat")
            return result, scheduled

        result, scheduled = asyncio.run(run())

        self.assertEqual(result.action, Action.RESPONSE)
        self.assertIn("128x64", result.response)
        self.assertEqual(len(scheduled), 1)


if __name__ == "__main__":
    unittest.main()
