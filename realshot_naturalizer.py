"""DeAI Humanizer Skill.

The module turns AI-looking image prompts or image-edit requests into realistic
photography directions. It can also apply a conservative local post-processing
pass to an image file when Pillow is available.

The safety boundary is intentional: this is for visual-quality and photographic
realism improvements, not for bypassing AI detectors, removing watermarks,
stripping provenance, or reconstructing redacted private information.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import os
import re
import random
from typing import Mapping, Sequence

__all__ = [
    "__version__",
    "SYSTEM_PROMPT",
    "PROMPT_TEMPLATES",
    "SUPPORTED_MODES",
    "AIFeature",
    "NaturalizeResult",
    "ImageNaturalizeResult",
    "detect_ai_features",
    "infer_scenario",
    "analyze_prompt",
    "build_edit_instruction",
    "humanize_prompt",
    "naturalize_image",
    "transform_prompt",
]


__version__ = "0.1.0"


SUPPORTED_MODES = (
    "auto",
    "portrait",
    "graduation",
    "id_photo",
    "street_shot",
    "street",
    "product",
    "interior",
    "generic",
)


@dataclass(frozen=True)
class FeatureRule:
    """A detectable AI-looking feature and its realistic replacement hint."""

    name: str
    patterns: tuple[str, ...]
    replacement_hint: str
    weight: float


@dataclass(frozen=True)
class AIFeature:
    """Feature detected in the source prompt."""

    name: str
    score: float
    evidence: tuple[str, ...]
    replacement_hint: str


@dataclass(frozen=True)
class SafetyResult:
    allowed: bool
    reason: str | None = None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class ScenarioConfig:
    """Scenario-specific settings used to build prompts and edit instructions."""

    keywords: tuple[str, ...]
    camera: str
    composition: str
    lighting: str
    realism_rules: tuple[str, ...]
    edit_rules: tuple[str, ...]
    negative_rules: tuple[str, ...]
    template: str


@dataclass(frozen=True)
class NaturalizeResult:
    """Full prompt-humanizing result for integrations that need metadata."""

    original_prompt: str
    mode: str
    ai_score: float
    detected_features: tuple[AIFeature, ...]
    realistic_prompt: str | None
    edit_instruction: str | None
    warnings: tuple[str, ...] = ()
    blocked: bool = False
    block_reason: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ImageNaturalizeResult:
    """Result returned by the optional local image post-processing helper."""

    input_path: str
    output_path: str
    mode: str
    intensity: float
    applied_adjustments: tuple[str, ...]
    edit_instruction: str


SYSTEM_PROMPT = """You are DeAI Humanizer, a rule-based photo realism editor.

Goal:
Rewrite image descriptions and image-edit requests so the result looks like a
real camera or phone photograph instead of a polished AI render.

Rules:
- Preserve the subject, identity cues, wardrobe, setting, activity, mood, and
  main objects unless the user explicitly asks to change them.
- Soften AI-looking perfection: plastic skin, poreless faces, perfect lighting,
  empty or over-perfect eyes, over-saturation, over-HDR, symmetry, render
  language, excessive sharpness, and poster-like cleanliness.
- Use plausible camera logic: 35mm or 50mm lens, imperfect available light,
  real focus hierarchy, candid composition, natural shadows, material texture,
  slight grain/noise, reduced saturation, and restrained contrast.
- For existing-image edits, describe practical retouching actions rather than
  pretending the image's provenance has changed.
- Preserve privacy redactions. Do not restore hidden text, IDs, faces, personal
  records, watermarks, metadata, or provenance signals.
- Return clean, paste-ready photographic instructions.
"""


AI_FEATURE_RULES: tuple[FeatureRule, ...] = (
    FeatureRule(
        name="plastic_or_over_smooth_skin",
        patterns=(
            r"\bflawless(?:ly)?(?:\s+smooth)?\s+skin\b",
            r"\bover[-\s]?smooth(?:ed)?\s+skin\b",
            r"\bporeless\s+skin\b",
            r"\bporcelain\s+skin\b",
            r"\bplastic\s+skin\b",
            r"\bairbrushed\s+skin\b",
            r"\bbeauty[-\s]?retouched\s+skin\b",
            r"皮肤(?:太)?光滑",
            r"磨皮",
            r"无毛孔",
            r"瓷肌",
            r"塑料(?:感)?皮肤",
            r"美颜(?:感)?",
            r"假白",
        ),
        replacement_hint="natural skin texture with pores, small blemishes, and real shadow transitions",
        weight=0.22,
    ),
    FeatureRule(
        name="empty_or_overperfect_eyes",
        patterns=(
            r"\b(?:empty|hollow|lifeless|dead|vacant)[-\s]?(?:looking\s+)?eyes?\b",
            r"\b(?:blank|vacant|rigid|frozen|dead)\s+(?:stare|gaze)\b",
            r"\b(?:glassy|glass-like|doll-like|uncanny|ai[-\s]?looking)\s+eyes?\b",
            r"\b(?:pure|bright|unnaturally|perfectly)\s+white\s+(?:sclera|eye whites?)\b",
            r"\b(?:identical|rigid|frozen|hard)\s+(?:eye\s+)?catchlights?\b",
            r"\b(?:flat|solid|featureless)\s+(?:black\s+)?pupils?\b",
            r"眼睛(?:空洞|呆滞|无神)",
            r"(?:空洞|呆滞|无神)(?:的)?眼(?:睛|神)",
            r"(?:直勾勾|僵硬)(?:的)?(?:注视|眼神|目光)",
            r"眼白(?:太|过于|非常)?白",
            r"(?:纯白|惨白)(?:的)?眼白",
            r"(?:反光|高光|眼神光)(?:太|过于)?(?:僵硬|固定|对称)",
            r"(?:瞳孔|虹膜)(?:没有|缺少|缺乏)(?:层次|细节)",
            r"(?:只有|纯|全是)黑色瞳孔",
            r"(?:假眼|玻璃眼|塑料眼珠)",
        ),
        replacement_hint=(
            "detailed iris and pupil tonal variation, off-white sclera, subtle "
            "tear-film sheen, natural light-consistent catchlights, soft gaze, "
            "and real under-eye shadows"
        ),
        weight=0.17,
    ),
    FeatureRule(
        name="perfect_lighting",
        patterns=(
            r"\bperfect(?:ly)?\s+(?:lit|lighting|illumination)\b",
            r"\bflawless\s+lighting\b",
            r"\bperfect\s+studio\s+light(?:ing)?\b",
            r"\bunrealistically\s+soft\s+light(?:ing)?\b",
            r"\bshadowless\s+light(?:ing)?\b",
            r"完美(?:的)?光线",
            r"完美(?:的)?打光",
            r"棚拍光",
            r"电影级(?:光线|打光)",
            r"均匀(?:的)?光",
            r"没有阴影",
            r"影棚级",
        ),
        replacement_hint="imperfect available light with mild shadows and uneven falloff",
        weight=0.18,
    ),
    FeatureRule(
        name="over_saturation_or_hdr",
        patterns=(
            r"\bover[-\s]?saturat(?:ed|ion)\s+colors?\b",
            r"\bultra[-\s]?saturat(?:ed|ion)\s+colors?\b",
            r"\bhyper[-\s]?saturat(?:ed|ion)\s+colors?\b",
            r"\bover[-\s]?saturat(?:ed|ion)\b",
            r"\bultra[-\s]?saturat(?:ed|ion)\b",
            r"\bhyper[-\s]?saturat(?:ed|ion)\b",
            r"\bneon\s+colors?\b",
            r"\bvibrant\s+colors?\b",
            r"\bextremely\s+colorful\b",
            r"\bhdr\b",
            r"过饱和",
            r"高饱和",
            r"颜色(?:太|很)?鲜艳",
            r"色彩(?:爆炸|太艳|通透)",
            r"蓝天(?:太|很)?蓝",
            r"红色(?:太|很)?红",
            r"滤镜(?:太)?重",
            r"过度hdr",
        ),
        replacement_hint="reduced saturation, softer highlight rolloff, and restrained contrast",
        weight=0.16,
    ),
    FeatureRule(
        name="excessive_sharpness",
        patterns=(
            r"\b(?:8k|16k|32k|uhd)\b",
            r"\brazor[-\s]?sharp\b",
            r"\bcrystal[-\s]?clear\b",
            r"\bultra[-\s]?detailed\b",
            r"\bhighly\s+detailed\b",
            r"超清",
            r"高清",
            r"极致细节",
            r"细节拉满",
            r"锐利",
            r"过度锐化",
            r"每个细节都清楚",
        ),
        replacement_hint="real focus hierarchy with natural sharpness falloff",
        weight=0.14,
    ),
    FeatureRule(
        name="symmetry_or_pose_perfection",
        patterns=(
            r"\bperfect(?:ly)?\s+symmetr(?:y|ical)\b",
            r"\bmirror[-\s]?symmetr(?:y|ical)\b",
            r"\bsymmetrical\s+face\b",
            r"\bperfect\s+facial\s+symmetry\b",
            r"完美(?:的)?对称",
            r"对称(?:脸|构图|姿势)",
            r"标准姿势",
            r"端正",
            r"完全居中",
            r"摆拍(?:感)?",
        ),
        replacement_hint="natural asymmetry and candid body language",
        weight=0.12,
    ),
    FeatureRule(
        name="render_or_ai_jargon",
        patterns=(
            r"\bmasterpiece\b",
            r"\bbest\s+quality\b",
            r"\boctane\s+render\b",
            r"\bunreal\s+engine\b",
            r"\bvray\b",
            r"\bcgi\b",
            r"\b3d\s+render\b",
            r"\bdigital\s+art\b",
            r"\bartstation\b",
            r"\btrending\s+on\s+artstation\b",
            r"\baward[-\s]?winning\b",
            r"\bai[-\s]?generated(?:\s+look)?\b",
            r"\bai[-\s]?looking\b",
            r"\bai\s+look\b",
            r"\bsynthetic\s+look\b",
            r"\bgenerated\s+look\b",
            r"\blooks?\s+like\s+ai\b",
            r"ai(?:生成|感|味)",
            r"生成(?:感|图)",
            r"渲染(?:感)?",
            r"cg(?:感)?",
            r"3d(?:感|渲染)?",
            r"大片(?:感)?",
            r"海报(?:感)?",
            r"商业样片",
            r"梦幻(?:感)?",
        ),
        replacement_hint="real-camera photographic language and everyday physical detail",
        weight=0.20,
    ),
    FeatureRule(
        name="too_clean_environment",
        patterns=(
            r"\bspotless\b",
            r"\bperfectly\s+clean\b",
            r"\bempty\s+perfect\s+background\b",
            r"过于干净",
            r"没有杂物",
            r"环境(?:太)?完美",
            r"背景(?:太)?干净",
            r"空无一人",
        ),
        replacement_hint="small real-life distractions, physical clutter, and believable contact shadows",
        weight=0.10,
    ),
)


PROMPT_TEMPLATES: Mapping[str, str] = {
    "portrait": (
        "Realistic portrait photograph of {subject}, shot on a {camera}, "
        "{composition}, {lighting}, natural skin texture with visible pores, "
        "minor blemishes, detailed irises and pupil tonal variation, off-white "
        "sclera, subtle moist tear-film sheen, small light-consistent catchlights, "
        "a soft non-staring gaze, real under-eye shadows, slight hair flyaways, "
        "subtle sensor noise and fine grain, reduced saturation and restrained contrast"
        "{corrections}."
    ),
    "graduation": (
        "Realistic graduation photograph of {subject}, shot on a {camera}, "
        "{composition}, {lighting}, believable gown fabric folds, bouquet wrap, "
        "hand pressure, ground shadows, natural skin texture, soft expressive "
        "gaze with subtle tear-film sheen and light-consistent catchlights, "
        "real under-eye shadows, subtle sensor noise and fine grain, reduced "
        "saturation in sky, flowers, and campus "
        "colors{corrections}."
    ),
    "id_photo": (
        "Realistic ID-style photograph of {subject}, shot on a {camera}, "
        "{composition}, {lighting}, natural skin texture, detailed irises, "
        "off-white sclera, subtle tear-film sheen, restrained catchlights, "
        "neutral gaze and preserved under-eye shadows, slight sensor noise, "
        "reduced saturation, neutral background, practical document-photo "
        "realism, preserving all privacy redactions and never restoring hidden "
        "information{corrections}."
    ),
    "street_shot": (
        "Realistic street photograph of {subject}, shot on a {camera}, "
        "{composition}, {lighting}, small real-life background clutter, slight "
        "motion softness where natural, subtle sensor noise and fine grain, "
        "reduced saturation, restrained contrast, documentary everyday "
        "atmosphere{corrections}."
    ),
    "product": (
        "Realistic product photograph of {subject}, shot on a {camera}, "
        "{composition}, {lighting}, physical contact shadows, material-specific "
        "reflections, tiny dust and texture, natural edge softness, subtle sensor "
        "noise, reduced saturation and restrained contrast{corrections}."
    ),
    "interior": (
        "Realistic interior photograph of {subject}, shot on a {camera}, "
        "{composition}, {lighting}, natural light falloff, imperfect wall and "
        "floor textures, lived-in details, realistic corner brightness, subtle "
        "sensor noise, reduced saturation and restrained contrast{corrections}."
    ),
    "generic": (
        "Realistic photograph of {subject}, shot on a {camera}, {composition}, "
        "{lighting}, natural texture and small real-world imperfections, real "
        "focus hierarchy, subtle sensor noise and fine grain, reduced saturation "
        "and restrained contrast{corrections}."
    ),
}


SCENARIO_CONFIGS: Mapping[str, ScenarioConfig] = {
    "portrait": ScenarioConfig(
        keywords=(
            "portrait",
            "headshot",
            "close-up",
            "close up",
            "face",
            "selfie",
            "profile picture",
            "人像",
            "肖像",
            "头像",
            "自拍",
            "半身照",
            "面部",
            "写真",
        ),
        camera="50mm lens",
        composition="eye-level handheld framing with a candid slight off-center crop",
        lighting="imperfect window light with mild shadow falloff",
        realism_rules=(
            "Keep pores, subtle skin unevenness, small blemishes, and real facial shadows.",
            "Keep detailed irises, subtle tear-film sheen, light-consistent catchlights, and natural under-eye shadows.",
            "Let hair and clothing have slight flyaways, wrinkles, and natural clumps.",
            "Avoid beauty-filter reshaping and perfect symmetry.",
        ),
        edit_rules=(
            "Reduce plastic skin smoothing while keeping the person recognizable.",
            "Replace flat pupils, pure-white sclera, and rigid catchlights with layered eye detail and a soft natural gaze.",
            "Lower excessive sharpening, saturation, and beauty-filter whitening.",
            "Unify face, hair, clothing, and background under one plausible light direction.",
        ),
        negative_rules=(
            "No poreless plastic skin or artificial beauty-filter face reshaping.",
            "No glassy empty eyes, pure-white sclera, mirrored catchlights, or fixed straight-ahead stare.",
            "No shadowless studio-perfect lighting unless explicitly requested.",
            "No CGI, render, poster, or hyper-clean commercial sample look.",
        ),
        template=PROMPT_TEMPLATES["portrait"],
    ),
    "graduation": ScenarioConfig(
        keywords=(
            "graduation",
            "graduate",
            "commencement",
            "cap and gown",
            "diploma",
            "campus ceremony",
            "毕业",
            "学位服",
            "学士服",
            "硕士服",
            "博士服",
            "校园",
            "校门",
            "花束",
            "毕业照",
        ),
        camera="50mm lens",
        composition="candid post-ceremony framing with a slightly uneven background",
        lighting="mixed outdoor campus light with mild shadows and uneven highlights",
        realism_rules=(
            "Keep campus context, crowds, signage, gown fabric folds, flowers, and ground shadows.",
            "Tone down overly blue sky, neon flowers, and overly vivid academic robe colors.",
            "Keep visible eyes moist but not tearful, with natural catchlights, iris detail, and soft emotional focus.",
            "Keep the subject attractive but not excessively retouched.",
        ),
        edit_rules=(
            "Reduce over-bright highlights and overly saturated campus colors.",
            "Make skin, hands, hair, gown edges, bouquet wrap, and shoes physically believable.",
            "If the eyes are visible, restore subtle tear-film sheen, iris depth, natural catchlights, and under-eye shadows.",
            "Keep the candid graduation-day atmosphere instead of a poster-template look.",
        ),
        negative_rules=(
            "No synthetic poster-style graduation template.",
            "No perfectly symmetrical pose or fully flawless retouched skin.",
            "No equally sharp background text, distant people, and foreground subject.",
        ),
        template=PROMPT_TEMPLATES["graduation"],
    ),
    "id_photo": ScenarioConfig(
        keywords=(
            "id photo",
            "id-photo",
            "passport",
            "visa photo",
            "driver license",
            "driving license",
            "identification photo",
            "document photo",
            "证件照",
            "证件",
            "护照",
            "签证",
            "身份证",
            "驾驶证",
            "学生证",
            "校园卡",
            "卡片",
        ),
        camera="50mm lens",
        composition=(
            "straight-on administrative framing with tiny natural asymmetry and "
            "a practical snapshot feel"
        ),
        lighting="plain room light with slight unevenness, not studio-perfect",
        realism_rules=(
            "Preserve all redactions and never infer hidden names, numbers, addresses, or records.",
            "Keep card edges, lamination, paper or plastic texture, shadows, and hand pressure realistic.",
            "Keep visible eyes neutral and anatomically detailed, with restrained catchlights and natural under-eye shadows.",
            "Use practical document-photo realism rather than a generated prop look.",
        ),
        edit_rules=(
            "Preserve and strengthen privacy masking; do not restore covered text or faces.",
            "Realize card thickness, edge shadows, lamination, and hand pressure.",
            "If a face is visible, keep off-white sclera, iris detail, subtle tear-film sheen, and a neutral non-staring gaze.",
            "Keep phone close-up depth of field readable but naturally soft in the background.",
        ),
        negative_rules=(
            "No reconstruction of blurred, covered, cropped, or redacted private information.",
            "No fake hands, extra-long fingers, or perfectly smooth hand skin.",
            "No perfectly flat sticker-like card edges.",
        ),
        template=PROMPT_TEMPLATES["id_photo"],
    ),
    "street_shot": ScenarioConfig(
        keywords=(
            "street",
            "sidewalk",
            "crosswalk",
            "subway",
            "metro",
            "alley",
            "market",
            "urban",
            "city candid",
            "街拍",
            "街头",
            "路边",
            "人行道",
            "斑马线",
            "地铁",
            "城市",
            "咖啡店",
            "餐厅",
            "探店",
            "旅行",
            "生活照",
        ),
        camera="35mm lens",
        composition="handheld candid composition with natural subject placement",
        lighting="available street light with uneven shadows and real ambient spill",
        realism_rules=(
            "Keep small environment clutter, passersby, signage, table items, or daily-life distractions.",
            "Allow slight motion blur, imperfect framing, and practical background mess.",
            "Avoid a hyper-clean commercial street set.",
        ),
        edit_rules=(
            "Add a candid snapshot feel through less perfect framing and natural environmental integration.",
            "Reduce heavy filters, over-HDR, and over-clean background surfaces.",
            "Keep ambient light direction, reflections, and shadows consistent.",
        ),
        negative_rules=(
            "No spotless commercial sample street scene.",
            "No over-posed fashion-campaign look unless requested.",
            "No over-sharpened background with every sign and passerby equally crisp.",
        ),
        template=PROMPT_TEMPLATES["street_shot"],
    ),
    "product": ScenarioConfig(
        keywords=(
            "product",
            "e-commerce",
            "ecommerce",
            "packaging",
            "bottle",
            "box",
            "商品",
            "产品",
            "电商",
            "包装",
            "详情页",
            "海报",
            "瓶子",
            "盒子",
        ),
        camera="50mm lens",
        composition="practical tabletop framing with believable physical contact",
        lighting="single softbox or window light with imperfect reflections and contact shadows",
        realism_rules=(
            "Use physical contact shadows and material-specific reflections.",
            "Keep tiny dust, label texture, edge softness, and believable surface marks.",
            "Avoid 3D-rendered perfection and impossible reflections.",
        ),
        edit_rules=(
            "Add believable contact shadows, surface texture, and material-specific highlight behavior.",
            "Reduce sterile 3D-render smoothness and overly sharp product edges.",
            "Keep labels and packaging consistent; do not invent regulated claims.",
        ),
        negative_rules=(
            "No CGI product render look or impossible floating shadows.",
            "No perfectly dust-free textureless surface.",
            "No physically impossible reflections.",
        ),
        template=PROMPT_TEMPLATES["product"],
    ),
    "interior": ScenarioConfig(
        keywords=(
            "interior",
            "room",
            "living room",
            "bedroom",
            "office",
            "showroom",
            "室内",
            "房间",
            "客厅",
            "卧室",
            "办公室",
            "展厅",
            "家装",
            "装修",
        ),
        camera="35mm lens",
        composition="natural room-height framing with believable verticals and lived-in placement",
        lighting="window or practical indoor light with real falloff and darker corners",
        realism_rules=(
            "Show realistic light falloff and imperfect wall, floor, and furniture textures.",
            "Keep small lived-in details and natural corner brightness differences.",
            "Avoid architectural-render cleanliness unless explicitly requested.",
        ),
        edit_rules=(
            "Reduce 3D-render highlights and make wall, floor, fabric, and wood textures physical.",
            "Keep darker corners, practical lamp spill, and natural exposure differences.",
            "Add subtle lived-in detail without changing the room layout.",
        ),
        negative_rules=(
            "No 3D-render showroom perfection or textureless walls.",
            "No equally bright corners and physically impossible lighting.",
            "No unrelated furniture or layout changes.",
        ),
        template=PROMPT_TEMPLATES["interior"],
    ),
    "generic": ScenarioConfig(
        keywords=(),
        camera="35mm lens",
        composition="candid documentary composition with a slight off-center crop",
        lighting="imperfect available light with mild shadow falloff",
        realism_rules=(
            "Use one plausible main light source and natural shadows.",
            "Reduce saturation, over-sharpening, over-HDR, and plastic textures.",
            "Keep small imperfections, real focus hierarchy, and camera-like grain.",
        ),
        edit_rules=(
            "Reduce synthetic smoothness, saturation, excessive sharpening, and HDR contrast.",
            "Add subtle grain, natural shadow transitions, and believable material texture.",
            "Keep the original subject and scene structure intact.",
        ),
        negative_rules=(
            "No CGI, poster, render, or hyper-clean generated look.",
            "No metadata stripping, watermark removal, or provenance-hiding request.",
            "No reconstruction of hidden or redacted private information.",
        ),
        template=PROMPT_TEMPLATES["generic"],
    ),
}


SCENARIO_PREFIX_PATTERNS: Mapping[str, tuple[str, ...]] = {
    "portrait": (
        r"^(?:a|an|the)?\s*(?:realistic\s+)?portrait(?:\s+photo(?:graph)?)?\s+of\s+",
        r"^(?:a|an|the)?\s*(?:realistic\s+)?headshot\s+of\s+",
        r"^(?:a|an|the)?\s*(?:realistic\s+)?portrait(?:\s+photo(?:graph)?)?\s*[,，:：-]\s*",
        r"^(?:a|an|the)?\s*(?:realistic\s+)?headshot\s*[,，:：-]\s*",
        r"^(?:真实)?(?:人像|肖像|头像|自拍|写真)(?:照片|照|图)?(?:，|,|\s)*(?:of\s+)?",
    ),
    "graduation": (
        r"^(?:a|an|the)?\s*(?:realistic\s+)?graduation\s+(?:photo(?:graph)?|portrait|shot)\s+of\s+",
        r"^(?:a|an|the)?\s*(?:realistic\s+)?graduate\s+portrait\s+of\s+",
        r"^(?:a|an|the)?\s*(?:realistic\s+)?graduation\s+(?:photo(?:graph)?|portrait|shot)\s*[,，:：-]\s*",
        r"^(?:校园)?毕业(?:照片|照|写真|跟拍)?(?:，|,|\s)*(?:of\s+)?",
    ),
    "id_photo": (
        r"^(?:a|an|the)?\s*(?:realistic\s+)?(?:id|passport|visa|document)\s+photo\s+of\s+",
        r"^(?:a|an|the)?\s*(?:realistic\s+)?identification\s+photo\s+of\s+",
        r"^(?:a|an|the)?\s*(?:realistic\s+)?(?:id|passport|visa|document)\s+photo\s*[,，:：-]\s*",
        r"^(?:证件|护照|签证|身份证|学生证|校园卡)(?:照片|照|图)?(?:，|,|\s)*(?:of\s+)?",
    ),
    "street_shot": (
        r"^(?:a|an|the)?\s*(?:realistic\s+)?street\s+(?:photo(?:graph)?|shot)\s+of\s+",
        r"^(?:a|an|the)?\s*(?:realistic\s+)?urban\s+(?:photo(?:graph)?|shot)\s+of\s+",
        r"^(?:a|an|the)?\s*(?:realistic\s+)?(?:street|urban)\s+(?:photo(?:graph)?|shot)\s*[,，:：-]\s*",
        r"^(?:街拍|街头|城市|生活)(?:照片|照|图)?(?:，|,|\s)*(?:of\s+)?",
    ),
    "product": (
        r"^(?:a|an|the)?\s*(?:realistic\s+)?product\s+(?:photo(?:graph)?|shot)\s+of\s+",
        r"^(?:产品|商品|电商|包装)(?:照片|照|图)?(?:，|,|\s)*(?:of\s+)?",
    ),
    "interior": (
        r"^(?:a|an|the)?\s*(?:realistic\s+)?interior\s+(?:photo(?:graph)?|shot)\s+of\s+",
        r"^(?:室内|房间|客厅|卧室|办公室)(?:照片|照|图)?(?:，|,|\s)*(?:of\s+)?",
    ),
    "generic": (
        r"^(?:a|an|the)?\s*(?:realistic\s+)?(?:photo(?:graph)?|image|picture|shot)\s+of\s+",
        r"^(?:a|an|the)?\s*prompt\s+(?:for|of)\s+",
        r"^(?:图片|照片|画面|提示词)(?:，|,|\s)*(?:of\s+)?",
    ),
}


DETECTION_TERMS = (
    "detect",
    "detector",
    "ai detector",
    "aigc detection",
    "识别",
    "检测",
    "ai检测",
    "aigc检测",
    "平台检测",
    "审核",
    "风控",
    "watermark",
    "水印",
    "c2pa",
    "metadata",
    "元数据",
    "provenance",
    "来源凭证",
)

EVASION_TERMS = (
    "bypass",
    "evade",
    "avoid",
    "hide",
    "remove",
    "strip",
    "undetectable",
    "绕过",
    "规避",
    "躲过",
    "逃过",
    "不被",
    "隐藏",
    "去掉",
    "去除",
    "移除",
    "删除",
    "洗掉",
)

PRIVACY_RECONSTRUCTION_TERMS = (
    "restore redacted",
    "recover blurred",
    "unblur",
    "deblur private",
    "恢复打码",
    "还原打码",
    "去码",
    "去马赛克",
    "还原遮挡",
    "恢复遮挡",
    "看清身份证",
    "看清号码",
)


JARGON_PATTERNS: tuple[str, ...] = tuple(
    pattern for rule in AI_FEATURE_RULES for pattern in rule.patterns
)


def transform_prompt(input_text: str) -> str:
    """Return only the cleaned realistic photography prompt.

    This keeps the original simple API stable while the richer ``humanize_prompt``
    function exposes mode, score, features, warnings, and edit instructions.
    """

    result = humanize_prompt(input_text)
    if result.blocked:
        raise ValueError(result.block_reason or "request blocked")
    return result.realistic_prompt or ""


def humanize_prompt(
    input_text: str,
    mode: str = "auto",
    intensity: float = 0.75,
) -> NaturalizeResult:
    """Analyze a prompt and return a realistic prompt plus image-edit guidance."""

    raw_text = _require_text(input_text)
    selected_mode = _resolve_mode(mode, raw_text)
    intensity = _clamp(float(intensity), 0.0, 1.0)
    safety = _check_safety(raw_text)
    features = analyze_prompt(raw_text, selected_mode)
    ai_score = _score_features(features)
    warnings = tuple(safety.warnings)

    if not safety.allowed:
        return NaturalizeResult(
            original_prompt=raw_text,
            mode=selected_mode,
            ai_score=ai_score,
            detected_features=features,
            realistic_prompt=None,
            edit_instruction=None,
            warnings=warnings,
            blocked=True,
            block_reason=safety.reason,
        )

    subject = _clean_subject(raw_text, selected_mode)
    corrections = _build_corrections(features, intensity)
    config = SCENARIO_CONFIGS[selected_mode]
    realistic_prompt = _normalize_output(
        config.template.format(
            subject=subject,
            camera=config.camera,
            composition=config.composition,
            lighting=config.lighting,
            corrections=corrections,
        )
    )
    edit_instruction = build_edit_instruction(
        raw_text,
        mode=selected_mode,
        intensity=intensity,
        detected_features=features,
    )

    return NaturalizeResult(
        original_prompt=raw_text,
        mode=selected_mode,
        ai_score=ai_score,
        detected_features=features,
        realistic_prompt=realistic_prompt,
        edit_instruction=edit_instruction,
        warnings=warnings,
    )


def analyze_prompt(input_text: str, mode: str = "auto") -> tuple[AIFeature, ...]:
    """Return scored AI-like prompt features with matched evidence."""

    text = _require_text(input_text)
    lowered = text.lower()
    features: list[AIFeature] = []

    for rule in AI_FEATURE_RULES:
        evidence = _find_rule_evidence(rule.patterns, lowered)
        if not evidence:
            continue
        score = min(rule.weight * max(1, len(evidence)), rule.weight * 2.0)
        features.append(
            AIFeature(
                name=rule.name,
                score=round(score, 3),
                evidence=tuple(evidence),
                replacement_hint=rule.replacement_hint,
            )
        )

    selected_mode = _resolve_mode(mode, text)
    if selected_mode in {"product", "interior"} and not any(
        feature.name == "too_clean_environment" for feature in features
    ):
        config = SCENARIO_CONFIGS[selected_mode]
        features.append(
            AIFeature(
                name="physical_believability",
                score=0.08,
                evidence=(selected_mode,),
                replacement_hint=config.realism_rules[0],
            )
        )

    return tuple(features)


def detect_ai_features(input_text: str) -> tuple[str, ...]:
    """Detect AI-like prompt features by rule name."""

    return tuple(feature.name for feature in analyze_prompt(input_text))


def infer_scenario(input_text: str) -> str:
    """Infer the best prompt template from the input text."""

    return _resolve_mode("auto", input_text)


def build_edit_instruction(
    input_text: str,
    mode: str = "auto",
    intensity: float = 0.75,
    detected_features: Sequence[AIFeature] | None = None,
) -> str:
    """Build a paste-ready instruction for editing an existing image."""

    raw_text = _require_text(input_text)
    selected_mode = _resolve_mode(mode, raw_text)
    config = SCENARIO_CONFIGS[selected_mode]
    intensity = _clamp(float(intensity), 0.0, 1.0)
    features = tuple(detected_features) if detected_features is not None else analyze_prompt(raw_text, selected_mode)
    strength = _strength_label(intensity)
    target = _clean_subject(raw_text, selected_mode)
    feature_lines = _feature_instruction_lines(features)
    rule_lines = "\n".join(f"- {rule}" for rule in config.edit_rules)
    negative_lines = "\n".join(f"- {rule}" for rule in config.negative_rules)

    instruction = f"""DeAI Humanizer Edit Instruction
Mode: {selected_mode}
Realism strength: {strength}
Source scene: {target}

Edit actions:
{rule_lines}
{feature_lines}
- Add slight sensor noise or fine grain only where it helps break synthetic smoothness.
- Keep the original scene, identity cues, wardrobe, layout, and important objects intact.

Limits:
{negative_lines}
- Do not remove watermarks, strip metadata, hide provenance, or bypass platform detection.
- Preserve all privacy masks and redactions; never infer or restore hidden personal information.

Final target:
A believable real camera or phone photograph with imperfect light, natural texture,
reduced saturation, restrained contrast, and candid physical detail."""

    return _normalize_multiline(instruction)


def naturalize_image(
    input_path: str | os.PathLike[str],
    output_path: str | os.PathLike[str] | None = None,
    *,
    prompt: str = "Make this image look like a realistic camera photograph.",
    mode: str = "auto",
    intensity: float = 0.55,
    seed: int | None = 17,
) -> ImageNaturalizeResult:
    """Apply a conservative local naturalization pass to an image file.

    The operation is intentionally modest: reduce AI-like saturation, contrast,
    and over-sharpness, add fine grain, and introduce a subtle lens vignette.
    Use an actual image-editing model when geometry, hands, faces, or object
    structure need semantic correction.
    """

    try:
        from PIL import Image, ImageChops, ImageEnhance, ImageFilter, ImageOps
    except ImportError as exc:  # pragma: no cover - covered only in environments without Pillow
        raise RuntimeError("naturalize_image requires Pillow: pip install pillow") from exc

    source_path = Path(input_path)
    if not source_path.exists():
        raise FileNotFoundError(f"input image not found: {source_path}")
    if not source_path.is_file():
        raise ValueError(f"input path is not a file: {source_path}")

    intensity = _clamp(float(intensity), 0.0, 1.0)
    selected_mode = _resolve_mode(mode, prompt or source_path.name)
    output = Path(output_path) if output_path is not None else _default_output_path(source_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(source_path) as opened:
        original_format = opened.format
        original_info = dict(opened.info)
        image = ImageOps.exif_transpose(opened).convert("RGB")

    adjustments: list[str] = []

    saturation = 1.0 - 0.26 * intensity
    contrast = 1.0 - 0.10 * intensity
    sharpness = 1.0 - 0.22 * intensity
    brightness = 1.0 - 0.025 * intensity

    image = ImageEnhance.Color(image).enhance(saturation)
    adjustments.append(f"saturation x{saturation:.2f}")
    image = ImageEnhance.Contrast(image).enhance(contrast)
    adjustments.append(f"contrast x{contrast:.2f}")
    image = ImageEnhance.Sharpness(image).enhance(sharpness)
    adjustments.append(f"sharpness x{sharpness:.2f}")
    image = ImageEnhance.Brightness(image).enhance(brightness)
    adjustments.append(f"brightness x{brightness:.2f}")

    if intensity > 0:
        grain_alpha = 0.018 + 0.032 * intensity
        grain = _make_grain(image.size, seed=seed).convert("RGB")
        image = Image.blend(image, grain, grain_alpha)
        adjustments.append(f"fine grain alpha {grain_alpha:.3f}")

        vignette_strength = 0.035 + 0.075 * intensity
        image = _apply_vignette(
            image,
            vignette_strength,
            ImageChops=ImageChops,
            ImageEnhance=ImageEnhance,
            ImageFilter=ImageFilter,
        )
        adjustments.append(f"subtle vignette {vignette_strength:.3f}")

    save_kwargs = _metadata_save_kwargs(original_info, output)
    if original_format and output.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
        save_kwargs.setdefault("format", _save_format_for_path(output, original_format))
    if output.suffix.lower() in {".jpg", ".jpeg"}:
        save_kwargs.setdefault("quality", 94)
        save_kwargs.setdefault("subsampling", 1)

    image.save(output, **save_kwargs)

    instruction = build_edit_instruction(prompt or source_path.name, mode=selected_mode, intensity=intensity)
    return ImageNaturalizeResult(
        input_path=str(source_path),
        output_path=str(output),
        mode=selected_mode,
        intensity=intensity,
        applied_adjustments=tuple(adjustments),
        edit_instruction=instruction,
    )


def _check_safety(text: str) -> SafetyResult:
    lowered = text.lower()
    has_detection = any(term.lower() in lowered for term in DETECTION_TERMS)
    has_evasion = any(term.lower() in lowered for term in EVASION_TERMS)
    has_privacy_reconstruction = any(
        term.lower() in lowered for term in PRIVACY_RECONSTRUCTION_TERMS
    )

    if has_privacy_reconstruction:
        return SafetyResult(
            allowed=False,
            reason=(
                "Request asks to restore or infer hidden private information. "
                "DeAI Humanizer preserves redactions and only improves visual realism."
            ),
            warnings=("blocked_privacy_reconstruction",),
        )

    if has_detection and has_evasion:
        return SafetyResult(
            allowed=False,
            reason=(
                "Request appears to target detection, watermark, metadata, or provenance evasion. "
                "DeAI Humanizer only supports legitimate visual-quality realism improvements."
            ),
            warnings=("blocked_detection_or_provenance_evasion",),
        )

    warnings: list[str] = []
    if has_detection:
        warnings.append(
            "Use the result for visual realism only, not for platform detection or provenance evasion."
        )
    return SafetyResult(allowed=True, warnings=tuple(warnings))


def _resolve_mode(mode: str, text: str) -> str:
    normalized = (mode or "auto").strip().lower().replace("-", "_")
    if normalized == "street":
        normalized = "street_shot"

    if normalized != "auto":
        if normalized not in SCENARIO_CONFIGS:
            raise ValueError(f"unsupported mode: {mode}. supported modes: {SUPPORTED_MODES}")
        return normalized

    lowered = _require_text(text).lower()
    for scenario in ("id_photo", "graduation", "product", "interior", "street_shot", "portrait"):
        config = SCENARIO_CONFIGS[scenario]
        if any(keyword.lower() in lowered for keyword in config.keywords):
            return scenario
    return "generic"


def _require_text(input_text: str) -> str:
    if not isinstance(input_text, str):
        raise TypeError("input_text must be a string")

    normalized = _normalize_spaces(input_text)
    if not normalized:
        raise ValueError("input_text must not be empty")

    return normalized


def _find_rule_evidence(patterns: Sequence[str], lowered_text: str) -> list[str]:
    evidence: list[str] = []
    for pattern in patterns:
        match = re.search(pattern, lowered_text, flags=re.IGNORECASE)
        if match:
            matched = match.group(0).strip()
            if matched and matched not in evidence:
                evidence.append(matched)
    return evidence


def _score_features(features: Sequence[AIFeature]) -> float:
    return round(min(sum(feature.score for feature in features), 1.0), 3)


def _clean_subject(raw_text: str, scenario: str) -> str:
    subject = _normalize_spaces(raw_text)
    subject = _remove_leading_prompt_words(subject, scenario)
    subject = _remove_ai_descriptors_from_subject(subject)
    subject = _dedupe_comma_phrases(subject)
    subject = _trim_punctuation(subject)

    if not subject:
        return "the subject"

    return subject


def _remove_ai_descriptors_from_subject(text: str) -> str:
    cleaned = text
    for pattern in JARGON_PATTERNS:
        cleaned = re.sub(
            rf"(?:\s*[,;，；]\s*|\b(?:with|and|in)\s+)?{pattern}",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )

    cleaned = re.sub(
        r"\b(?:with|and|in)(?:\s+(?:a|an|the))?\s*(?=,|，|$)",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"[,，]\s*(?:with|and|in)\s*[,，]", ", ", cleaned, flags=re.IGNORECASE)
    return _normalize_delimiters(cleaned)


def _remove_leading_prompt_words(text: str, scenario: str) -> str:
    cleaned = text
    patterns = SCENARIO_PREFIX_PATTERNS.get(scenario, ())
    patterns += SCENARIO_PREFIX_PATTERNS["generic"]

    for pattern in patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

    return _normalize_spaces(cleaned)


def _build_corrections(features: Sequence[AIFeature], intensity: float) -> str:
    if not features:
        return ""

    max_items = 3 if intensity < 0.67 else 5
    hints: list[str] = []
    for feature in sorted(features, key=lambda item: item.score, reverse=True):
        hint = feature.replacement_hint
        if hint not in hints:
            hints.append(hint)
        if len(hints) >= max_items:
            break

    if not hints:
        return ""

    return ", specifically correcting for " + ", ".join(hints)


def _feature_instruction_lines(features: Sequence[AIFeature]) -> str:
    if not features:
        return ""

    lines = []
    for feature in sorted(features, key=lambda item: item.score, reverse=True)[:5]:
        lines.append(f"- Correct {feature.name.replace('_', ' ')}: {feature.replacement_hint}.")
    return "\n".join(lines) + "\n"


def _dedupe_comma_phrases(text: str) -> str:
    parts = [part.strip(" .;；,，") for part in re.split(r"[,，]", text)]
    output: list[str] = []
    seen: set[str] = set()

    for part in parts:
        if not part:
            continue
        key = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", part.lower()).strip()
        if not key or key in seen:
            continue
        seen.add(key)
        output.append(part)

    return ", ".join(output)


def _make_grain(size: tuple[int, int], seed: int | None) -> object:
    from PIL import Image

    width, height = size
    rng = random.Random(seed) if seed is not None else random.Random()
    if hasattr(rng, "randbytes"):
        data = rng.randbytes(width * height)
    else:  # pragma: no cover - for very old Python versions
        data = bytes(rng.randrange(256) for _ in range(width * height))
    return Image.frombytes("L", size, data)


def _apply_vignette(image: object, strength: float, *, ImageChops: object, ImageEnhance: object, ImageFilter: object) -> object:
    from PIL import Image, ImageDraw, ImageOps

    width, height = image.size
    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)
    inset_x = int(width * 0.05)
    inset_y = int(height * 0.05)
    draw.ellipse(
        (inset_x, inset_y, width - inset_x, height - inset_y),
        fill=255,
    )
    radius = max(8, int(min(width, height) * 0.18))
    center_mask = mask.filter(ImageFilter.GaussianBlur(radius=radius))
    edge_mask = ImageOps.invert(center_mask).point(lambda px: int(px * strength))
    darkened = ImageEnhance.Brightness(image).enhance(1.0 - strength)
    return Image.composite(darkened, image, edge_mask)


def _metadata_save_kwargs(info: Mapping[str, object], output_path: Path) -> dict:
    kwargs: dict = {}
    exif = info.get("exif")
    icc_profile = info.get("icc_profile")
    if exif and output_path.suffix.lower() in {".jpg", ".jpeg", ".webp"}:
        kwargs["exif"] = exif
    if icc_profile:
        kwargs["icc_profile"] = icc_profile
    return kwargs


def _save_format_for_path(path: Path, fallback: str) -> str:
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        return "JPEG"
    if suffix == ".png":
        return "PNG"
    if suffix == ".webp":
        return "WEBP"
    return fallback


def _default_output_path(input_path: Path) -> Path:
    return input_path.with_name(f"{input_path.stem}_realshot{input_path.suffix}")


def _strength_label(intensity: float) -> str:
    if intensity < 0.34:
        return "light"
    if intensity < 0.67:
        return "medium"
    return "strong"


def _clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))


def _normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _normalize_delimiters(text: str) -> str:
    text = re.sub(r"\s*[,;，；]\s*", ", ", text)
    text = re.sub(r"(?:,\s*){2,}", ", ", text)
    text = re.sub(r"\s+([,.，。])", r"\1", text)
    return _normalize_spaces(text)


def _trim_punctuation(text: str) -> str:
    return text.strip(" ,.;:-，。；：")


def _normalize_output(text: str) -> str:
    text = _normalize_delimiters(text)
    text = re.sub(r"\s+\.", ".", text)
    text = re.sub(r",\s*\.", ".", text)
    return text


def _normalize_multiline(text: str) -> str:
    lines = [line.rstrip() for line in text.strip().splitlines()]
    normalized: list[str] = []
    previous_blank = False
    for line in lines:
        is_blank = not line.strip()
        if is_blank and previous_blank:
            continue
        normalized.append(line)
        previous_blank = is_blank
    return "\n".join(normalized)


def _main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="DeAI Humanizer prompt and image helper.")
    subparsers = parser.add_subparsers(dest="command")

    prompt_parser = subparsers.add_parser("prompt", help="Rewrite a prompt as realistic photography.")
    prompt_parser.add_argument("text", help="Image description or prompt to transform.")
    prompt_parser.add_argument("--mode", default="auto", choices=SUPPORTED_MODES)
    prompt_parser.add_argument("--intensity", type=float, default=0.75)
    prompt_parser.add_argument("--with-edit-instruction", action="store_true")

    image_parser = subparsers.add_parser("image", help="Apply local naturalization to an image.")
    image_parser.add_argument("input_path")
    image_parser.add_argument("output_path", nargs="?")
    image_parser.add_argument("--prompt", default="Make this image look like a realistic camera photograph.")
    image_parser.add_argument("--mode", default="auto", choices=SUPPORTED_MODES)
    image_parser.add_argument("--intensity", type=float, default=0.55)

    args = parser.parse_args()
    if args.command in {None, "prompt"}:
        if args.command is None:
            parser.error("choose a command: prompt or image")
        result = humanize_prompt(args.text, mode=args.mode, intensity=args.intensity)
        if result.blocked:
            raise SystemExit(result.block_reason or "request blocked")
        print(result.realistic_prompt)
        if args.with_edit_instruction:
            print()
            print(result.edit_instruction)
    elif args.command == "image":
        result = naturalize_image(
            args.input_path,
            args.output_path,
            prompt=args.prompt,
            mode=args.mode,
            intensity=args.intensity,
        )
        print(result.output_path)


if __name__ == "__main__":
    _main()
