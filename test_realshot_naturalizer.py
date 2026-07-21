import tempfile
import unittest
from pathlib import Path

from realshot_naturalizer import (
    analyze_prompt,
    build_edit_instruction,
    detect_ai_features,
    humanize_prompt,
    infer_scenario,
    naturalize_image,
    transform_prompt,
)


class RealShotNaturalizerTests(unittest.TestCase):
    def test_detects_ai_like_features(self) -> None:
        features = detect_ai_features(
            "Portrait with flawless smooth skin, perfect lighting, "
            "oversaturated colors, perfect facial symmetry, 8k masterpiece"
        )

        self.assertEqual(
            features,
            (
                "plastic_or_over_smooth_skin",
                "perfect_lighting",
                "over_saturation_or_hdr",
                "excessive_sharpness",
                "symmetry_or_pose_perfection",
                "render_or_ai_jargon",
            ),
        )

    def test_transforms_portrait_prompt(self) -> None:
        result = transform_prompt(
            "Portrait of a woman with flawless smooth skin, perfect lighting, "
            "oversaturated colors, perfect symmetry, 8k masterpiece"
        )
        lowered = result.lower()

        self.assertIn("realistic portrait photograph", lowered)
        self.assertIn("50mm lens", lowered)
        self.assertIn("natural skin texture", lowered)
        self.assertIn("subtle sensor noise", lowered)
        self.assertIn("reduced saturation", lowered)
        self.assertIn("candid", lowered)
        self.assertNotIn("flawless smooth skin", lowered)
        self.assertNotIn("8k", lowered)
        self.assertNotIn("masterpiece", lowered)

    def test_detects_and_corrects_unrealistic_eyes(self) -> None:
        features = detect_ai_features(
            "Portrait with lifeless eyes, pure white sclera, and rigid catchlights"
        )
        result = transform_prompt(
            "Portrait of a woman with lifeless eyes, pure white sclera, and rigid catchlights"
        )
        lowered = result.lower()

        self.assertIn("empty_or_overperfect_eyes", features)
        self.assertIn("detailed irises", lowered)
        self.assertIn("tear-film sheen", lowered)
        self.assertIn("light-consistent catchlights", lowered)
        self.assertIn("soft non-staring gaze", lowered)
        self.assertIn("real under-eye shadows", lowered)
        self.assertNotIn("lifeless eyes", lowered)
        self.assertNotIn("pure white sclera", lowered)
        self.assertNotIn("rigid catchlights", lowered)

    def test_detects_chinese_empty_eye_language(self) -> None:
        features = detect_ai_features(
            "人像照片，眼神空洞，眼白太白，眼神光过于僵硬，只有黑色瞳孔"
        )

        self.assertEqual(features, ("empty_or_overperfect_eyes",))

    def test_plain_scene_prefix_does_not_become_subject(self) -> None:
        result = transform_prompt(
            "portrait, flawless smooth skin, perfect lighting, oversaturated colors"
        )

        self.assertIn("Realistic portrait photograph of the subject", result)
        self.assertNotIn("of portrait", result)

    def test_chinese_graduation_prompt_uses_reference_rules(self) -> None:
        result = humanize_prompt(
            "校园毕业照，学位服，蓝天很蓝，花束颜色太鲜艳，皮肤太光滑，整体像AI生成",
            mode="auto",
            intensity=0.8,
        )

        self.assertFalse(result.blocked)
        self.assertEqual(result.mode, "graduation")
        self.assertGreater(result.ai_score, 0.5)
        self.assertIn("Realistic graduation photograph", result.realistic_prompt or "")
        self.assertIn("gown fabric folds", result.realistic_prompt or "")
        self.assertIn("bouquet wrap", result.realistic_prompt or "")
        self.assertIn("privacy", result.edit_instruction or "")

    def test_removes_english_ai_generated_jargon(self) -> None:
        result = transform_prompt(
            "Graduation photo of a student in cap and gown, over saturated colors, "
            "plastic skin, AI generated look"
        )

        self.assertIn("Realistic graduation photograph", result)
        self.assertNotIn("AI generated look", result)
        self.assertNotIn("plastic skin", result)

    def test_uses_id_photo_template(self) -> None:
        result = transform_prompt("Passport photo of a man, flawless lighting")

        self.assertIn("Realistic ID-style photograph", result)
        self.assertIn("neutral background", result)
        self.assertIn("50mm lens", result)
        self.assertIn("preserving all privacy redactions", result)

    def test_uses_street_template(self) -> None:
        result = transform_prompt("Street shot of a cyclist at a city crosswalk")

        self.assertIn("Realistic street photograph", result)
        self.assertIn("35mm lens", result)
        self.assertIn("handheld candid", result)

    def test_product_and_interior_modes(self) -> None:
        self.assertEqual(infer_scenario("产品包装图，边缘太像3D渲染"), "product")
        self.assertEqual(infer_scenario("室内客厅效果图，过于干净"), "interior")

        product = transform_prompt("Product photo of a perfume bottle, CGI render, perfect clean background")
        interior = transform_prompt("Interior image of a living room, 3D render, spotless")

        self.assertIn("Realistic product photograph", product)
        self.assertIn("physical contact shadows", product)
        self.assertIn("Realistic interior photograph", interior)
        self.assertIn("natural light falloff", interior)

    def test_builds_edit_instruction(self) -> None:
        instruction = build_edit_instruction(
            "街拍照片，颜色过饱和，背景太干净，摆拍感强",
            mode="auto",
        )

        self.assertIn("DeAI Humanizer Edit Instruction", instruction)
        self.assertIn("Mode: street_shot", instruction)
        self.assertIn("Edit actions:", instruction)
        self.assertIn("Final target:", instruction)
        self.assertIn("Do not remove watermarks", instruction)

    def test_portrait_edit_instruction_includes_eye_actions(self) -> None:
        instruction = build_edit_instruction(
            "Portrait with glassy eyes and a vacant stare",
            mode="portrait",
        )

        self.assertIn("flat pupils", instruction)
        self.assertIn("subtle tear-film sheen", instruction)
        self.assertIn("under-eye shadows", instruction)
        self.assertNotIn("Source scene: Portrait and a", instruction)

    def test_blocks_detection_evasion_request(self) -> None:
        result = humanize_prompt("帮我去除AI水印并绕过平台AI检测", mode="auto")

        self.assertTrue(result.blocked)
        self.assertIsNone(result.realistic_prompt)
        self.assertIn("detection", result.block_reason or "")

        with self.assertRaises(ValueError):
            transform_prompt("bypass AI detector and remove metadata")

    def test_analyze_prompt_returns_evidence(self) -> None:
        features = analyze_prompt("portrait, plastic skin, perfect lighting")

        self.assertTrue(features)
        self.assertTrue(all(feature.evidence for feature in features))
        self.assertTrue(all(feature.replacement_hint for feature in features))

    def test_naturalize_image_outputs_file(self) -> None:
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow is not installed")

        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "source.png"
            output = Path(temp_dir) / "output.png"
            Image.new("RGB", (64, 48), (240, 80, 220)).save(source)

            result = naturalize_image(
                source,
                output,
                prompt="Portrait with over saturated colors and plastic skin",
                intensity=0.6,
                seed=1,
            )

            self.assertTrue(output.exists())
            self.assertEqual(result.output_path, str(output))
            self.assertIn("fine grain", " ".join(result.applied_adjustments))
            with Image.open(output) as edited:
                self.assertEqual(edited.size, (64, 48))
                self.assertNotEqual(edited.getpixel((10, 10)), (240, 80, 220))

    def test_rejects_empty_input(self) -> None:
        with self.assertRaises(ValueError):
            transform_prompt("   ")


if __name__ == "__main__":
    unittest.main()
