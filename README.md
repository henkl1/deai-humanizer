# DeAI Humanizer

DeAI Humanizer is a small, dependency-light Python toolkit for rewriting AI-looking image prompts and image-edit requests into realistic photography directions.

It focuses on visual quality: natural skin or material texture, believable eyes and gaze, imperfect available light, slight grain, candid composition, reduced saturation, believable shadows, and real camera logic.

It is not a tool for bypassing AI detectors, removing watermarks, stripping metadata, hiding provenance, or reconstructing redacted private information.

## Features

- Detects AI-looking prompt features such as plastic skin, empty or over-perfect eyes, perfect lighting, over-saturation, over-sharpening, symmetry, render jargon, and overly clean environments.
- Rebuilds visible eyes with correct iris-pupil separation, transparent corneal reflections, a subtle tear-film waterline, scleral shading, eyelid anatomy, and coherent gaze.
- Rewrites prompts into realistic camera photography prompts.
- Builds paste-ready edit instructions for existing image editors.
- Supports portrait, graduation, ID/document photo, street/lifestyle, product, interior, and generic scenes.
- Provides optional local image post-processing with Pillow: reduced saturation, softer sharpness, fine grain, and subtle vignette.
- Includes a Codex repo skill under `.agents/skills/deai-humanizer`.

## Installation

From source:

```bash
git clone https://github.com/your-name/deai-humanizer.git
cd deai-humanizer
python -m pip install -e .
```

For local image post-processing:

```bash
python -m pip install -e ".[image]"
```

## Quick Start

```python
from realshot_naturalizer import transform_prompt

prompt = transform_prompt(
    "Portrait of a woman with flawless smooth skin, perfect lighting, "
    "oversaturated colors, perfect symmetry, 8k masterpiece"
)

print(prompt)
```

For richer metadata and edit instructions:

```python
from realshot_naturalizer import humanize_prompt

result = humanize_prompt(
    "Graduation photo of a student in cap and gown, over saturated colors, plastic skin",
    mode="auto",
    intensity=0.8,
)

print(result.mode)
print(result.realistic_prompt)
print(result.edit_instruction)
```

Optional local image processing:

```python
from realshot_naturalizer import naturalize_image

result = naturalize_image(
    "input.png",
    "output.png",
    prompt="Street shot, over saturated colors, plastic skin, spotless background",
    intensity=0.55,
)

print(result.output_path)
```

## CLI

Prompt rewrite:

```bash
deai-humanizer prompt "street shot, over saturated colors, plastic skin"
```

With edit instruction:

```bash
deai-humanizer prompt "graduation photo, AI generated look, plastic skin" --with-edit-instruction
```

Local image processing:

```bash
deai-humanizer image input.png output.png --prompt "make this look like a realistic phone photo"
```

You can also run the module directly:

```bash
python realshot_naturalizer.py prompt "portrait, perfect lighting, poreless skin"
```

## Public API

- `transform_prompt(input_text: str) -> str`
- `humanize_prompt(input_text: str, mode: str = "auto", intensity: float = 0.75) -> NaturalizeResult`
- `build_edit_instruction(input_text: str, mode: str = "auto", intensity: float = 0.75) -> str`
- `analyze_prompt(input_text: str, mode: str = "auto") -> tuple[AIFeature, ...]`
- `detect_ai_features(input_text: str) -> tuple[str, ...]`
- `infer_scenario(input_text: str) -> str`
- `naturalize_image(input_path, output_path=None, prompt="", mode="auto", intensity=0.55) -> ImageNaturalizeResult`

## Scene Modes

- `auto`
- `portrait`
- `graduation`
- `id_photo`
- `street_shot`
- `product`
- `interior`
- `generic`

## Tests

```bash
python -m unittest -v
```

## GitHub Publishing Checklist

Before publishing:

```bash
python -m unittest -v
python -m py_compile realshot_naturalizer.py test_realshot_naturalizer.py
```

Then initialize and push:

```bash
git init
git add .
git commit -m "Initial open source release"
git branch -M main
git remote add origin https://github.com/your-name/deai-humanizer.git
git push -u origin main
```

The reference archive `deai-humanizer.zip` is intentionally ignored by `.gitignore` and should not be published unless you explicitly want to include it.

## Safety Boundary

DeAI Humanizer is designed for legitimate image-quality and photo-realism work.

It refuses or redirects requests involving detection evasion, watermark removal, metadata stripping, provenance hiding, or restoration of redacted private information.

## License

MIT License. See `LICENSE`.
