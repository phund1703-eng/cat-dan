"""
Shared scene schema helpers (Task 2.1 — source citation schema).

Canonical scene shape additions:
    "fact": "khẳng định khoa học cốt lõi của cảnh",
    "sources": [{"title": "...", "url": "https://...", "publisher": "...", "accessed_date": "YYYY-MM-DD"}]

Stage 6 — story beats (kể chuyện theo nhịp lời thoại):
    "beats": [
        {
            "narration_part": "trích nguyên văn một cụm lời thoại của beat",
            "elements": [
                {"role": "focal|secondary|prop|label", "keyword": "white blood cell",
                 "action": "enter|exit|emphasize|swap_pose",
                 "from": "left|right|top|bottom", "to": "left|right|top|bottom",
                 "pose": "ten tu the (chi dung voi swap_pose)"}
            ],
            "emphasis_words": ["tu nhan manh hien theo nhip noi"]
        }
    ]

Used by gemini_client (post-parse), script_generator (post-generate) and
source_gate (audit) so every script carries fact/sources/beats consistently.
"""

from typing import Any, Dict, List
import re


def normalize_source(source: Any) -> Dict[str, str]:
    """Coerces one raw source entry into the canonical source dict shape."""
    if not isinstance(source, dict):
        return {"title": "", "url": str(source or "").strip(), "publisher": "", "accessed_date": ""}
    return {
        "title": str(source.get("title") or ""),
        "url": str(source.get("url") or "").strip(),
        "publisher": str(source.get("publisher") or ""),
        "accessed_date": str(source.get("accessed_date") or ""),
    }


def normalize_scene(scene: Any) -> Any:
    """
    Ensures a scene dict carries `fact` (str), `sources` (list of source dicts)
    and `beats` (list of story-beat dicts, Stage 6).

    Mutates and returns the scene. `fact` falls back to `core_meaning` when the
    model did not provide one; `sources` defaults to an empty list (never invented);
    `beats` falls back to a deterministic heuristic choreography built from the
    scene's own narration/keywords when the model did not provide beats.
    """
    if not isinstance(scene, dict):
        return scene
    fact = scene.get("fact")
    if not isinstance(fact, str) or not fact.strip():
        scene["fact"] = str(scene.get("core_meaning") or "")
    raw_sources = scene.get("sources")
    if not isinstance(raw_sources, list):
        raw_sources = []
    scene["sources"] = [normalize_source(s) for s in raw_sources]
    normalize_beats(scene)
    return scene


def normalize_script_scenes(script: Any) -> Any:
    """Applies normalize_scene to every scene of a script dict. Returns the script."""
    if isinstance(script, dict):
        scenes = script.get("scenes")
        if isinstance(scenes, list):
            for scene in scenes:
                normalize_scene(scene)
    return script


# ---------------------------------------------------------------------------
# Stage 6 — story beats
# ---------------------------------------------------------------------------

BEAT_ACTIONS = ("enter", "exit", "emphasize", "swap_pose")
BEAT_ROLES = ("focal", "secondary", "prop", "label")
BEAT_DIRECTIONS = ("left", "right", "top", "bottom")
MAX_BEATS = 6
MAX_ELEMENTS_PER_BEAT = 6
MAX_EMPHASIS_WORDS = 5

_VI_EN_STOPWORDS = frozenset(
    "và của các những một cái là được trong với cho từ đến để khi mà thì như có không này kia đó rất sẽ đã đang hãy bị được".split()
    + "the a an of and to in on for with is are was were be as at by from that this it its".split()
)


def normalize_beat_element(el: Any) -> Dict[str, str]:
    """Coerces one raw beat element into the canonical element dict shape."""
    if not isinstance(el, dict):
        return {"role": "prop", "keyword": "", "action": "enter",
                "from": "left", "to": "right", "pose": ""}
    role = str(el.get("role") or "prop").strip().lower()
    action = str(el.get("action") or "enter").strip().lower()
    from_dir = str(el.get("from") or "left").strip().lower()
    to_dir = str(el.get("to") or "right").strip().lower()
    return {
        "role": role if role in BEAT_ROLES else "prop",
        "keyword": str(el.get("keyword") or "").strip(),
        "action": action if action in BEAT_ACTIONS else "enter",
        "from": from_dir if from_dir in BEAT_DIRECTIONS else "left",
        "to": to_dir if to_dir in BEAT_DIRECTIONS else "right",
        "pose": str(el.get("pose") or "").strip(),
    }


def normalize_beat(beat: Any, narration: str = "") -> Dict[str, Any]:
    """Coerces one raw beat into the canonical beat dict shape."""
    if not isinstance(beat, dict):
        beat = {}
    part = beat.get("narration_part")
    if not isinstance(part, str) or not part.strip():
        part = narration
    raw_elements = beat.get("elements")
    if not isinstance(raw_elements, list):
        raw_elements = []
    elements = [normalize_beat_element(e) for e in raw_elements[:MAX_ELEMENTS_PER_BEAT]]
    # Drop elements with empty keyword unless they are pure label/emphasis carriers.
    elements = [e for e in elements if e["keyword"] or e["role"] == "label"]
    raw_words = beat.get("emphasis_words")
    if not isinstance(raw_words, list):
        raw_words = []
    emphasis = [str(w).strip() for w in raw_words
                if isinstance(w, str) and w.strip()][:MAX_EMPHASIS_WORDS]
    return {
        "narration_part": part.strip(),
        "elements": elements,
        "emphasis_words": emphasis,
    }


def _split_narration_parts(narration: str, max_beats: int = 4) -> List[str]:
    """Splits narration into 2-4 verbatim parts on punctuation/word-count boundaries."""
    text = (narration or "").strip()
    if not text:
        return []
    chunks = [c.strip() for c in re.split(r"(?<=[,.!?;:])\s+", text) if c.strip()]
    if not chunks:
        chunks = [text]
    # Split over-long chunks by word count so a single long sentence still
    # yields multiple beats (each beat ~6-12 words).
    wordsplit: List[str] = []
    for ch in chunks:
        w = ch.split()
        while len(w) > 12:
            cut = len(w) // 2
            # Prefer cutting near a comma inside the chunk.
            wordsplit.append(" ".join(w[:cut]))
            w = w[cut:]
        wordsplit.append(" ".join(w))
    chunks = [c for c in wordsplit if c]
    # Merge small chunks so each part carries ~6-16 words.
    parts: List[str] = []
    buf = ""
    for ch in chunks:
        buf_words = len(buf.split())
        combined = (buf + " " + ch).strip()
        if buf and buf_words < 5 and len(combined.split()) <= 12:
            buf = combined
        else:
            if buf.strip():
                parts.append(buf.strip())
            buf = ch
    if buf.strip():
        parts.append(buf.strip())
    # Merge down to max_beats by joining the shortest neighbours.
    while len(parts) > max_beats:
        idx = min(range(len(parts) - 1), key=lambda i: len(parts[i]) + len(parts[i + 1]))
        parts[idx] = (parts[idx] + " " + parts[idx + 1]).strip()
        del parts[idx + 1]
    return parts


def _pick_emphasis_words(part: str, max_words: int = 2) -> List[str]:
    """Picks up to `max_words` long content words from a narration part (deterministic)."""
    words = re.findall(r"[A-Za-zÀ-ỹà-ỹ]+", part or "")
    cands = [w for w in words
             if len(w) >= 5 and w.lower() not in _VI_EN_STOPWORDS]
    # Longest first, stable order for ties.
    cands.sort(key=lambda w: (-len(w), words.index(w)))
    seen, out = set(), []
    for w in cands:
        lw = w.lower()
        if lw not in seen:
            seen.add(lw)
            out.append(w)
        if len(out) >= max_words:
            break
    return out


def build_heuristic_beats(scene: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Builds a deterministic 2-4 beat fallback choreography for a scene.

    Beat grammar (Threado-style): beat 1 focal enters, beat 2 secondary enters,
    beat 3 focal changes pose / emphasizes, beat 4+ secondary exits.
    Only uses keywords the scene already carries — never invents assets.
    """
    narration = str(scene.get("narration") or "")
    parts = _split_narration_parts(narration)
    if not parts:
        return []
    focal = str(scene.get("focal_keyword") or "").strip()
    secondary = str(scene.get("secondary_keyword") or "").strip()
    if secondary.lower() == "none":
        secondary = ""

    beats: List[Dict[str, Any]] = []
    for i, part in enumerate(parts):
        elements: List[Dict[str, str]] = []
        if i == 0 and focal:
            elements.append({"role": "focal", "keyword": focal, "action": "enter",
                             "from": "left", "to": "right", "pose": ""})
        elif i == 1 and secondary:
            elements.append({"role": "secondary", "keyword": secondary, "action": "enter",
                             "from": "right", "to": "left", "pose": ""})
            if focal:
                elements.append({"role": "focal", "keyword": focal, "action": "emphasize",
                                 "from": "left", "to": "right", "pose": ""})
        elif i == 2 and focal:
            elements.append({"role": "focal", "keyword": focal, "action": "swap_pose",
                             "from": "left", "to": "right", "pose": "alt"})
        elif i >= 3:
            if secondary:
                elements.append({"role": "secondary", "keyword": secondary, "action": "exit",
                                 "from": "right", "to": "right", "pose": ""})
            elif focal:
                elements.append({"role": "focal", "keyword": focal, "action": "emphasize",
                                 "from": "left", "to": "right", "pose": ""})
        emphasis = _pick_emphasis_words(part) if i in (1, 2) else []
        beats.append({
            "narration_part": part,
            "elements": elements,
            "emphasis_words": emphasis,
        })
    return beats


def normalize_beats(scene: Any) -> Any:
    """
    Ensures a scene dict carries a valid `beats` list.

    Keeps LLM-provided beats (sanitized); builds deterministic heuristic beats
    when missing/empty/invalid. Mutates and returns the scene.
    """
    if not isinstance(scene, dict):
        return scene
    raw = scene.get("beats")
    beats: List[Dict[str, Any]] = []
    if isinstance(raw, list) and raw:
        narration = str(scene.get("narration") or "")
        for b in raw[:MAX_BEATS]:
            nb = normalize_beat(b, narration)
            # Keep beats that actually say something or move something.
            if nb["narration_part"] or nb["elements"]:
                beats.append(nb)
    if not beats:
        beats = build_heuristic_beats(scene)
    scene["beats"] = beats
    return scene
