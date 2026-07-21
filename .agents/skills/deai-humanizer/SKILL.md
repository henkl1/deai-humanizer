---
name: deai-humanizer
description: Improve AI-looking image prompts, existing image edit requests, portraits, graduation photos, ID/document photos, street/lifestyle shots, product photos, and interior images into realistic camera or phone photography. Use when the user asks to reduce plastic AI style, make an image look more natural/real, remove synthetic polish, lower over-saturation, fix over-smooth skin, correct empty or glassy eyes, oversized black-dot pupils, missing iris or corneal reflections, rigid gaze, generate a realistic photography prompt, or create practical edit instructions. Do not use for bypassing AI detectors, watermark/provenance/metadata removal, or restoring redacted private information.
---

# DeAI Humanizer

Use this skill to convert AI-looking prompts or image-edit requests into realistic photography directions. The goal is visual quality and camera realism, not detection evasion.

## Workflow

1. Inspect the user's input and identify the scene mode:
   - `portrait`: faces, selfies, headshots, personal portraits.
   - `graduation`: campus photos, gowns, caps, bouquets, diploma scenes.
   - `id_photo`: ID cards, passport photos, document photos, student cards.
   - `street_shot`: street, travel, cafe, restaurant, lifestyle, candid scenes.
   - `product`: e-commerce, packaging, product, bottle, box, tabletop photos.
   - `interior`: rooms, offices, homes, showrooms, architectural interiors.
2. Refuse or redirect requests that ask to bypass AI detection, remove watermarks, strip metadata, hide provenance, or recover redacted private information.
3. Prefer the repository module `realshot_naturalizer.py` when available:
   - `transform_prompt(text)` returns only the realistic prompt.
   - `humanize_prompt(text, mode="auto", intensity=0.75)` returns prompt, edit instruction, score, warnings, and detected features.
   - `build_edit_instruction(text, mode="auto", intensity=0.75)` returns a paste-ready instruction for an image editor.
   - `naturalize_image(input_path, output_path=None, prompt="", mode="auto", intensity=0.55)` applies a conservative local Pillow post-process.
4. For existing images, output an edit instruction first. Use `naturalize_image` only when the user wants a local file processed and Pillow is available.
5. Preserve the user's subject, identity cues, clothing, composition, setting, and main objects unless they ask to change them.
6. Match eye detail to image scale: use the full optical eye stack for close-ups and headshots; for medium or wide shots, keep correct pupil size, iris visibility, corneal reflection, and gaze without forcing microscopic iris detail.

## Output Shape

For prompt-only work, return:

```text
Realistic Prompt:
...
```

For existing image editing, return:

```text
Edit Instruction:
...
```

If local image processing was run, also include the output file path and the high-level adjustments applied.

## Quality Rules

Load `references/realism-rules.md` when a scene needs detailed realism guidance or when revising outputs that still feel synthetic. For any face with visible eyes, apply its `Eyes And Gaze` rules and reuse the close-up correction block when the eyes are a major part of the frame.

Always include camera-realism cues:
- 35mm or 50mm lens logic.
- Imperfect available light.
- Natural skin or material texture.
- For visible eyes: keep the pupil naturally dark, preserve a visible textured iris around it, place environment reflections on the transparent cornea across the iris and pupil, retain a thin lower-lid waterline, scleral shadow, coherent gaze, and natural under-eye texture.
- Subtle sensor noise or fine grain.
- Candid or documentary composition.
- Reduced saturation and restrained contrast.
- Real shadows, contact, focus hierarchy, and small physical imperfections.
