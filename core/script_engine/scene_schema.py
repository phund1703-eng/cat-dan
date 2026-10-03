"""
Shared scene schema helpers (Task 2.1 — source citation schema).

Canonical scene shape additions:
    "fact": "khẳng định khoa học cốt lõi của cảnh",
    "sources": [{"title": "...", "url": "https://...", "publisher": "...", "accessed_date": "YYYY-MM-DD"}]

Used by gemini_client (post-parse), script_generator (post-generate) and
source_gate (audit) so every script carries fact/sources consistently.
"""

from typing import Any, Dict


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
    Ensures a scene dict carries `fact` (str) and `sources` (list of source dicts).

    Mutates and returns the scene. `fact` falls back to `core_meaning` when the
    model did not provide one; `sources` defaults to an empty list (never invented).
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
    return scene


def normalize_script_scenes(script: Any) -> Any:
    """Applies normalize_scene to every scene of a script dict. Returns the script."""
    if isinstance(script, dict):
        scenes = script.get("scenes")
        if isinstance(scenes, list):
            for scene in scenes:
                normalize_scene(scene)
    return script
