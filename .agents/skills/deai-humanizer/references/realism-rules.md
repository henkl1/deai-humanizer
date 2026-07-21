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

- Treat the pupil correctly: it is a naturally dark aperture, not a surface that needs texture. Size it for the scene's light and keep both pupils plausibly consistent. Do not let a large black disk erase the surrounding iris.
- Keep the iris clearly visible around the pupil. Show restrained radial fibers, crypts, a darker outer limbal ring, a subtle inner ring, and small color variations without making the iris look illustrated or over-sharpened.
- Model the cornea as a transparent convex surface over both iris and pupil. Place soft, environment-shaped window, street, or room reflections across that surface; do not paint a single white dot inside the pupil.
- Keep left and right corneal reflections consistent with one light source but slightly different in shape or position because of eye angle and anatomy. Avoid perfectly mirrored highlights.
- Add a thin moist tear-film sheen and a narrow lower-lid waterline. Keep the wetness subtle so the person does not look tearful unless the intended emotion calls for it.
- Use naturally off-white sclera with upper-lid shadow, mild warm or cool variation, and restrained tiny vessels when resolution supports them. Avoid pure white or uniformly bright eye whites.
- Preserve eyelid anatomy: upper-lid occlusion over the iris, lower-lid rim, inner-corner tear duct, irregular eyelashes, tiny lash shadows, and real skin transition around the eye.
- Preserve lower-lid structure, real under-eye shadow, mild skin variation, and slight fatigue when appropriate instead of erasing the whole eye area.
- Keep both eyes aimed at one plausible fixation point. Preserve the intended gaze direction and expression without a rigid stare, crossed eyes, or diverging pupils.
- Scale detail to framing. In close-ups and headshots, use the full eye stack above. In medium or wide shots, prioritize pupil size, visible iris, corneal reflection, coherent gaze, and eyelid shadow; do not force microscopic iris fibers that the camera could not resolve.
- Avoid glass eyes, doll-like eyes, oversized black-dot pupils, missing irises, pure-white sclera, painted-dot highlights, identical reflections, excessive wetness, artificial tears, or invented texture inside the pupil.

For a close-up or headshot, reuse this correction block:

```text
Preserve the person's identity, eye shape, eye color, gaze direction, and expression. Keep each pupil as a naturally dark aperture sized for the ambient light, with a clearly visible iris surrounding it. Restore restrained radial iris fibers, crypts, limbal-ring depth, and subtle color variation. Model the cornea as a transparent convex surface and place soft environment-shaped reflections across both the iris and pupil, consistent with the actual window or room light rather than a painted white dot. Add a thin tear-film sheen and lower-lid waterline, upper-lid shadow over naturally off-white sclera, realistic eyelid rims and lashes, coherent binocular gaze, and natural under-eye texture with slight fatigue. Do not enlarge the pupils until the iris disappears, add detail inside the pupil, change eye color, exaggerate veins, or make the eyes tearful.
```

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
