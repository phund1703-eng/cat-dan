"""
Stage 6 Step 2 — BeatChoreographer: dựng timeline chuyển động từ story beats.

Đầu vào: 1 scene dict (đã có `beats` theo schema ở core/script_engine/scene_schema.py)
         + thời lượng audio TTS thật của scene.
Đầu ra: {
    "timeline":   [actions cho MotionTimelineEngine],
    "cast":       {"hero": {...}, "secondary": {...}, "action_<slug>": {...}},
                  # base configs (position chuẩn hoá, visible...) cho GbroAdapter
    "beat_timing": [{"narration_part": str, "start": float, "end": float}],
    "labels":     [{"text": str, "start": float, "end": float, "position": [x, y]}],
    "target_by_keyword": {keyword: target},
}

Ánh xạ beat -> action:
  enter    -> CONVERGE_WRAP  (bay vào từ ngoài biên, trước giờ spawn thì ẩn)
  exit     -> EXIT_SLIDE     (trượt ra theo hướng rồi visible=False)
  emphasize-> COMPRESS_SQUASH x2 (nảy to -> về 1.0, vì engine giữ scale cuối)
  swap_pose-> SWAP_ASSET     (đổi asset_variant; renderer vẽ variant tương ứng)
  approach -> TRANSLATE_NAV  (tiến lại gần nhân vật khác, dừng cách ~260px)
  absorb   -> ABSORB_DISSOLVE (bị nuốt: teo dần rồi biến mất)

Nhịp beat neo theo số từ của narration_part trên tổng thời lượng audio thật,
nên khớp nhịp nói dù TTS dài/ngắn.
"""

from typing import Any, Dict, List, Tuple
import re
import zlib

try:
    from core.script_engine.scene_schema import normalize_beats
except Exception:  # pragma: no cover - defensive khi import độc lập
    def normalize_beats(scene):  # type: ignore
        return scene


HEAD_RESERVE = 0.4   # giây đầu dành cho lắp ráp nền
TAIL_RESERVE = 0.5   # giây cuối giữ khung

# Vị trí nghỉ (chuẩn hoá 0..1) theo vai trò.
_REST_POS = {
    "hero": [0.36, 0.58],
    "secondary": [0.66, 0.42],
}
_PROP_SLOTS = [[0.20, 0.30], [0.80, 0.30], [0.20, 0.75], [0.80, 0.75]]
_LABEL_POS = [0.5, 0.16]

_OFFSCREEN = {
    "left": (-1.2, 0.0),
    "right": (1.2, 0.0),
    "top": (0.0, -1.2),
    "bottom": (0.0, 1.2),
}


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", (text or "").lower()).strip("_")
    return s[:24] or "prop"


class BeatChoreographer:
    """Dựng timeline + cast layout từ story beats của 1 scene."""

    def __init__(self, width: int = 1080, height: int = 1920):
        self.width = width
        self.height = height

    # ------------------------------------------------------------------
    def choreograph(self, scene: Dict[str, Any], audio_duration: float) -> Dict[str, Any]:
        normalize_beats(scene)
        beats: List[Dict[str, Any]] = scene.get("beats") or []
        duration = float(audio_duration or 0) or float(scene.get("duration") or 5.0)
        duration = max(2.0, duration)

        beat_timing = self._plan_beat_timing(beats, duration)
        cast: Dict[str, Dict[str, Any]] = {}
        target_by_keyword: Dict[str, str] = {}
        timeline: List[Dict[str, Any]] = []
        labels: List[Dict[str, Any]] = []
        prop_idx = 0

        # Lượt 1a: đăng ký toàn bộ element thật (giữ thứ tự xuất hiện).
        for beat in beats:
            for el in beat.get("elements") or []:
                keyword = str(el.get("keyword") or "").strip()
                role = el.get("role") or "prop"
                if not keyword or keyword in target_by_keyword:
                    continue
                if role == "focal" and "hero" not in cast:
                    target = "hero"
                elif role == "secondary" and "secondary" not in cast:
                    target = "secondary"
                else:
                    target = f"action_{_slug(keyword)}_{prop_idx}"
                    prop_idx += 1
                target_by_keyword[keyword] = target
                cast[target] = self._make_cast_entry(target, role, keyword)

        # Lượt 1b: đăng ký keyword chỉ xuất hiện trong "target" của approach
        # (có vị trí để tính điểm đến; mặc định ẩn vì không có action enter).
        for beat in beats:
            for el in beat.get("elements") or []:
                if str(el.get("action") or "") != "approach":
                    continue
                approached = str(el.get("target") or "").strip()
                if approached and approached not in target_by_keyword:
                    at = f"action_{_slug(approached)}_{prop_idx}"
                    prop_idx += 1
                    target_by_keyword[approached] = at
                    entry = self._make_cast_entry(at, "secondary", approached)
                    entry["visible"] = False
                    cast[at] = entry

        # Lượt 2: sinh actions theo từng beat.
        for bi, (beat, (bstart, bend)) in enumerate(zip(beats, beat_timing)):
            for el in beat.get("elements") or []:
                keyword = str(el.get("keyword") or "").strip()
                action = el.get("action") or "enter"
                if not keyword:
                    continue
                target = target_by_keyword.get(keyword)
                if target is None:
                    continue
                rest_px = self._to_px(cast[target]["position"])
                timeline.extend(
                    self._actions_for(target, action, el, rest_px, bstart, bend,
                                      cast, target_by_keyword)
                )
            emphasis_text = " ".join(beat.get("emphasis_words") or []).strip()
            if emphasis_text:
                labels.append({
                    "text": emphasis_text,
                    "start": round(bstart + 0.15, 3),
                    "end": round(bend, 3),
                    "position": list(_LABEL_POS),
                })

        # Sắp xếp timeline theo thời gian bắt đầu để engine duyệt ổn định.
        timeline.sort(key=lambda a: self._action_start(a))
        return {
            "timeline": timeline,
            "cast": cast,
            "beat_timing": [
                {"narration_part": b.get("narration_part", ""),
                 "start": round(s, 3), "end": round(e, 3)}
                for b, (s, e) in zip(beats, beat_timing)
            ],
            "labels": labels,
            "target_by_keyword": target_by_keyword,
        }

    # ------------------------------------------------------------------
    def _plan_beat_timing(
        self, beats: List[Dict[str, Any]], duration: float
    ) -> List[Tuple[float, float]]:
        usable = max(0.5, duration - HEAD_RESERVE - TAIL_RESERVE)
        counts = [max(1, len((b.get("narration_part") or "").split())) for b in beats]
        total = sum(counts) or 1
        timing, cursor = [], HEAD_RESERVE
        for i, c in enumerate(counts):
            span = usable * c / total
            start = cursor
            end = HEAD_RESERVE + usable if i == len(counts) - 1 else cursor + span
            timing.append((round(start, 3), round(end, 3)))
            cursor = end
        return timing

    def _make_cast_entry(
        self, target: str, role: str, keyword: str
    ) -> Dict[str, Any]:
        if target == "hero":
            pos = list(_REST_POS["hero"])
        elif target == "secondary":
            pos = list(_REST_POS["secondary"])
        else:
            pos = list(_PROP_SLOTS[zlib.crc32(target.encode()) % len(_PROP_SLOTS)])
        return {
            "keyword": keyword,
            "role": role,
            "target": target,
            "position": pos,          # chuẩn hoá 0..1 (engine tự đổi sang px)
            "scale": 1.0,
            "visible": target in ("hero", "secondary"),
            "pose": "",
        }

    def _to_px(self, norm_pos: List[float]) -> List[float]:
        return [float(norm_pos[0]) * self.width, float(norm_pos[1]) * self.height]

    def _offscreen_px(self, direction: str, rest_px: List[float]) -> List[float]:
        dx, dy = _OFFSCREEN.get(direction, _OFFSCREEN["right"])
        return [rest_px[0] + dx * self.width, rest_px[1] + dy * self.height]

    def _actions_for(
        self,
        target: str,
        action: str,
        el: Dict[str, Any],
        rest_px: List[float],
        bstart: float,
        bend: float,
        cast: Dict[str, Dict[str, Any]],
        target_by_keyword: Dict[str, str],
    ) -> List[Dict[str, Any]]:
        if action == "enter":
            frm = str(el.get("from") or "left")
            dx, dy = _OFFSCREEN.get(frm, _OFFSCREEN["left"])
            return [{
                "target": target,
                "action": "CONVERGE_WRAP",
                "start_time": round(bstart + 0.05, 3),
                "start_offset": [dx * self.width, dy * self.height],
                "duration": 0.85,
                "steps": 4,
            }]
        if action == "exit":
            to = str(el.get("to") or "right")
            t0 = round(bstart + 0.1, 3)
            return [{
                "target": target,
                "action": "EXIT_SLIDE",
                "time_range": [t0, round(t0 + 0.8, 3)],
                "direction": to if to in ("left", "right", "top", "bottom") else "right",
                "start_pos": [round(rest_px[0], 1), round(rest_px[1], 1)],
                "steps": 4,
            }]
        if action == "emphasize":
            t0 = round(bstart + 0.1, 3)
            return [
                {"target": target, "action": "COMPRESS_SQUASH",
                 "time_range": [t0, round(t0 + 0.28, 3)],
                 "scale_x": 1.32, "scale_y": 0.78, "steps": 2},
                {"target": target, "action": "COMPRESS_SQUASH",
                 "time_range": [round(t0 + 0.28, 3), round(t0 + 0.56, 3)],
                 "scale_x": 1.0, "scale_y": 1.0, "steps": 2},
            ]
        if action == "swap_pose":
            # SWAP_ASSET: engine đặt asset_variant; renderer (Step 4) vẽ variant
            # tương ứng, không có variant thì giữ ảnh gốc.
            return [{
                "target": target,
                "action": "SWAP_ASSET",
                "swap_time": round(bstart + 0.1, 3),
                "pose": str(el.get("pose") or "alt"),
            }]
        if action == "approach":
            # Tiến lại gần nhân vật khác: trượt tới điểm cách mục tiêu ~260px.
            approached_kw = str(el.get("target") or "").strip()
            approached_id = target_by_keyword.get(approached_kw)
            if approached_id is None or approached_id == target:
                # Không xác định được mục tiêu: chọn nhân vật khác đầu tiên.
                approached_id = next(
                    (tid for tid in cast if tid != target), None)
            if approached_id is None:
                return []
            dest_norm = cast[approached_id]["position"]
            dest_px = self._to_px(dest_norm)
            dx, dy = dest_px[0] - rest_px[0], dest_px[1] - rest_px[1]
            dist = max(1.0, (dx * dx + dy * dy) ** 0.5)
            gap = 260.0
            stop = max(0.0, dist - gap) / dist
            end_px = [rest_px[0] + dx * stop, rest_px[1] + dy * stop]
            t0 = round(bstart + 0.05, 3)
            return [{
                "target": target,
                "action": "TRANSLATE_NAV",
                "time_range": [t0, round(t0 + 1.1, 3)],
                "start_pos": [round(rest_px[0], 1), round(rest_px[1], 1)],
                "end_pos": [round(end_px[0], 1), round(end_px[1], 1)],
                "steps": 5,
                "max_tilt_deg": 12.0,
                "wave_amplitude": 20.0,
            }]
        if action == "absorb":
            # Bị nuốt chửng: teo dần rồi biến mất (kẻ săn "ăn" con mồi).
            return [{
                "target": target,
                "action": "ABSORB_DISSOLVE",
                "absorb_time": round(bstart + 0.15, 3),
                "duration": 0.7,
                "steps": 4,
            }]
        return []

    @staticmethod
    def _action_start(a: Dict[str, Any]) -> float:
        for k in ("start_time", "spawn_time", "swap_time", "absorb_time"):
            if k in a:
                return float(a[k])
        tr = a.get("time_range")
        if isinstance(tr, (list, tuple)) and tr:
            return float(tr[0])
        return 0.0
