# DeAI Humanizer Realism Rules

## Universal

- Use one plausible main light source and allow mild unevenness.
- Reduce over-saturation, over-sharpening, over-HDR, plastic skin, and render-like cleanliness.
- Keep natural asymmetry, small imperfections, fabric wrinkles, hair flyaways, dust, fingerprints, and believable shadows.
- Do not make every plane equally sharp; preserve foreground/background focus hierarchy.
- Prefer candid camera logic over commercial-poster perfection unless the user asks for a polished campaign.

## Portrait

- Keep pores, subtle skin texture, slight unevenness, minor blemishes, and real shadow transitions.
- Hair should include flyaways or natural clumps, not perfect helmet-like strands.
- Avoid face reshaping, poreless beauty filters, mirror symmetry, and shadowless studio light.
- Use 50mm portrait logic unless the scene clearly calls for a phone snapshot.

## Eyes And Gaze

Apply these rules whenever a face has visible eyes:

- Diagnose synthetic eyes by looking for flat black pupils, missing iris variation, pure-white sclera, rigid or mirrored catchlights, a dry glassy surface, fixed straight-ahead staring, and missing lower-lid or under-eye shadows.
- Keep layered iris texture and pupil tonal variation. Use naturally off-white sclera with restrained local color variation; do not exaggerate veins or redness.
- Add a subtle moist tear-film or waterline sheen, especially along the lower lid. Keep it understated so the person does not look tearful unless the scene calls for that emotion.
- Make catchlights small, soft, and consistent with the scene's actual window, street, or room light. Left and right reflections may differ slightly with eye angle and anatomy.
- Preserve lower-lid structure, real under-eye shadow, mild skin variation, and slight fatigue when appropriate instead of erasing the whole eye area.
- Use a soft, emotionally present gaze rather than a rigid, direct stare. Preserve the subject's intended identity, gaze direction, and expression.
- Avoid glass eyes, doll-like eyes, pure-white eye whites, identical catchlights, featureless pupils, excessive wetness, or artificial tears.

## Graduation

- Keep campus context, school signage, flowers, gown/cap, crowds, and background activity.
- Tone down pure blue sky, overly vivid flowers, and neon-like academic robe color.
- Make gown folds, bouquet wrapping, hand grip, shoes, and ground shadows physically believable.
- The result should feel like a graduation-day candid, not a template poster.

## ID Or Document Photo

- Preserve all redactions; never restore blurred, masked, cropped, or covered private information.
- Make card edges, lamination, paper/plastic texture, shadows, and hand pressure realistic.
- Hands need visible knuckle structure, skin color variation, nail edges, and natural proportions.
- Phone close-up depth of field should keep the card readable while the background remains naturally soft.

## Street Or Lifestyle

- Keep small environment clutter, passersby, table items, signage, reflections, and real-life distractions.
- Allow slight motion blur, imperfect framing, non-centered subjects, and exposure variation.
- Avoid empty, hyper-clean environments unless the scene explicitly requires them.

## Product

- Use physical contact shadows, material-specific reflections, tiny dust, and surface texture.
- Avoid 3D-rendered edge perfection, impossible reflections, and perfectly floating products.
- Keep labels and packaging consistent; do not invent regulated claims.

## Interior

- Show realistic light falloff and imperfect wall, floor, furniture, fabric, and wood textures.
- Corners should not be equally bright; allow practical lamp spill and natural exposure differences.
- Keep layout stable unless the user asks for redesign.

## Local Image Post-Processing

When using `naturalize_image`, keep intensity conservative:
- `0.25-0.45`: light cleanup for already plausible photos.
- `0.50-0.65`: normal reduction of AI polish.
- `0.70-0.85`: stronger reduction for very saturated or plastic images.

The local processor adjusts pixels only. It cannot semantically fix hands, faces, text, anatomy, or impossible geometry; for those cases, generate an edit instruction for an image-editing model.
