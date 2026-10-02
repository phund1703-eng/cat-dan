"""
AutoVideoFactory — MultiElementSceneDesigner (Phase 2)
Phân tích cú pháp câu thoại kịch bản tiếng Việt thành Bản thiết kế Cảnh đa vật thể tương tác (Multi-Element Scene Layout):
- Chủ ngữ -> Vật thể HERO (AGENT): 40-60% khung hình, vai trò chủ động
- Động từ -> Kiểu tương tác (INTERACTION): PRESSING, EXAMINING, ENGULFING, MEASURING...
- Tân ngữ -> Vật thể BỊ TÁC ĐỘNG (SECONDARY / TARGET): 25-38% khung hình, đặt ở vị trí bị tác động
- Trạng ngữ / Bối cảnh -> Đồ họa môi trường (environment_graphic): microscope_reticle, coordinate_grid, ruler_scale...
"""

import os
import re
import json
import asyncio
from typing import Dict, Any, List, Optional
from loguru import logger
from dotenv import load_dotenv
import google.generativeai as genai

from .verb_semantic_matcher import VerbSemanticMatcher

load_dotenv()


class MultiElementSceneDesigner:
    """
    Thiết kế bố cục cảnh đa vật thể tương tác vật lý dựa trên cú pháp câu văn:
    Cú pháp câu văn = Cú pháp cảnh collage
    """

    ARCHETYPE_COLORS = {
        "specimen_scientific": [
            {"name": "Deep Cobalt", "hex": "1D3557"},
            {"name": "Sage Green", "hex": "588157"},
            {"name": "Teal & Coral", "hex": "2A9D8F"}
        ],
        "geography_ocean": [
            {"name": "Deep Cobalt", "hex": "1D3557"},
            {"name": "Charcoal Kraft", "hex": "264653"},
            {"name": "Teal & Coral", "hex": "2A9D8F"}
        ],
        "industrial_social": [
            {"name": "Charcoal Kraft", "hex": "264653"},
            {"name": "Burnt Terracotta", "hex": "D44D22"},
            {"name": "Mustard Cardstock", "hex": "E9C46A"}
        ],
        "conceptual_duel": [
            {"name": "Plum & Gold", "hex": "4A235A"},
            {"name": "Burnt Terracotta", "hex": "D44D22"},
            {"name": "Charcoal Kraft", "hex": "264653"}
        ],
        "historical_relic": [
            {"name": "Mustard Cardstock", "hex": "E9C46A"},
            {"name": "Plum & Gold", "hex": "4A235A"},
            {"name": "Burnt Terracotta", "hex": "D44D22"}
        ]
    }

    def __init__(self):
        self.api_keys = []
        key1 = os.getenv("GEMINI_API_KEY_1") or os.getenv("GEMINI_API_KEY")
        key2 = os.getenv("GEMINI_API_KEY_2")
        for k in [key1, key2]:
            if k and k.strip() and not k.strip().startswith("your_") and k.strip() not in self.api_keys:
                self.api_keys.append(k.strip())
        self.current_key_idx = 0
        if self.api_keys:
            genai.configure(api_key=self.api_keys[0])
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
        self.matcher = VerbSemanticMatcher()

    def _switch_key(self):
        if len(self.api_keys) > 1:
            self.current_key_idx = (self.current_key_idx + 1) % len(self.api_keys)
            genai.configure(api_key=self.api_keys[self.current_key_idx])
            logger.warning(f"Switched Gemini key to index {self.current_key_idx}")

    async def design_scene(self, sentence: str, topic_context: str = "", scene_idx: int = 0) -> Dict[str, Any]:
        """
        Phân tích câu thoại và sinh JSON layout đa vật thể tương tác.
        """
        prompt = f"""
Bạn là Giám đốc Nghệ thuật & Kiến trúc sư Bố cục Collage Đa Vật Thể (Multi-Element Scene Designer).
Nhiệm vụ: Phân tích cú pháp câu thoại video tiếng Việt dưới đây để thiết kế một bố cục cảnh cắt dán gồm 2 vật thể tương tác vật lý (Hero và Secondary) trong khung hình dọc 1080x1920 (9:16).

Chủ đề chính: "{topic_context}"
Câu thoại: "{sentence}"

Quy tắc phân tích:
1. Chủ ngữ (Agent) -> `hero_element`: Vật thể chủ động, tỷ lệ scale từ 0.45 đến 0.60, thường đặt ở nửa trên hoặc trung tâm (position: [0.5, 0.42-0.48]).
2. Động từ -> `interaction_type`: Chọn 1 trong các kiểu tương tác vật lý: "EXAMINING" (soi/chiếu), "PRESSING" (đè ép), "ENGULFING" (bao vây/nuốt), "MEASURING" (đo đạc), "OPERATING" (thao tác), "POINTING" (chỉ thị).
3. Tân ngữ (Target) -> `secondary_element`: Vật thể bị tác động, tỷ lệ scale từ 0.25 đến 0.35, đặt ở vị trí tương ứng với hero (ví dụ nếu EXAMINING thì đặt bên dưới [0.5, 0.70-0.75], nếu PRESSING thì đặt ngay dưới bàn ép).
4. Bối cảnh -> `environment_graphic`: "microscope_reticle" (kính hiển vi), "coordinate_grid" (kinh vĩ hải trình), "ruler_scale" (thước đo kỹ thuật), "papyrus_frame" (bản thảo Ai Cập), "depth_contours" (đường đẳng sâu).
5. Archetype: "specimen_scientific", "geography_ocean", "industrial_social", "conceptual_duel", "historical_relic".
6. `has_pointing_hand`: true nếu câu văn có ý nhấn mạnh chỉ dẫn, ngược lại false.

Trả về DUY NHẤT định dạng JSON sau (không kèm markdown thừa):
{{
  "archetype": "specimen_scientific",
  "color_field": "Deep Cobalt",
  "color_hex": "1D3557",
  "interaction_type": "EXAMINING",
  "hero_element": {{
    "name": "vintage brass microscope",
    "prompt": "a vintage brass microscope",
    "scale": 0.55,
    "position": [0.5, 0.45],
    "rotation_deg": -5
  }},
  "secondary_element": {{
    "name": "red bacteria petri dish",
    "prompt": "a glass petri dish with red bacteria colonies",
    "scale": 0.32,
    "position": [0.5, 0.72],
    "rotation_deg": 3
  }},
  "environment_graphic": "microscope_reticle",
  "has_pointing_hand": false
}}
"""
        for attempt in range(len(self.api_keys) + 1):
            if not self.api_keys:
                break
            try:
                model = genai.GenerativeModel(self.model_name)
                resp = await asyncio.wait_for(
                    model.generate_content_async(
                        prompt,
                        generation_config=genai.types.GenerationConfig(
                            temperature=0.3,
                            response_mime_type="application/json"
                        )
                    ),
                    timeout=5.0
                )
                text = resp.text.strip()
                match = re.search(r'\{.*\}', text, re.DOTALL)
                if match:
                    data = json.loads(match.group(0))
                    # Validate required fields
                    if "hero_element" in data and "secondary_element" in data:
                        sanitized = self._sanitize_layout(data, scene_idx)
                        verb_entry = await self.matcher.match_sentence(sentence, topic_context)
                        return self.matcher.enrich_scene_layout(sanitized, sentence, verb_entry=verb_entry)
            except Exception as e:
                logger.warning(f"Gemini MultiElementSceneDesigner attempt {attempt} failed: {e}")
                self._switch_key()
                await asyncio.sleep(0.5)

        # Fallback Heuristic chuẩn xác
        logger.info(f"⚡ [MultiElementSceneDesigner] Kích hoạt Heuristic Fallback cho: {sentence[:30]}...")
        fallback_layout = self._heuristic_fallback(sentence, topic_context, scene_idx)
        verb_entry = await self.matcher.match_sentence(sentence, topic_context)
        return self.matcher.enrich_scene_layout(fallback_layout, sentence, verb_entry=verb_entry)

    def _sanitize_layout(self, data: Dict[str, Any], scene_idx: int) -> Dict[str, Any]:
        """Chuẩn hóa dữ liệu layout để đảm bảo vị trí và tỷ lệ luôn hoàn hảo."""
        arch = data.get("archetype", "specimen_scientific")
        if arch not in self.ARCHETYPE_COLORS:
            arch = "specimen_scientific"

        colors = self.ARCHETYPE_COLORS[arch]
        color_item = colors[scene_idx % len(colors)]

        data["archetype"] = arch
        data["color_field"] = data.get("color_field") or color_item["name"]
        data["color_hex"] = (data.get("color_hex") or color_item["hex"]).lstrip("#")

        hero = data.get("hero_element", {})
        hero["name"] = hero.get("name", "vintage hero object")
        hero["prompt"] = hero.get("prompt", hero["name"])
        hero["scale"] = max(0.40, min(0.65, float(hero.get("scale", 0.52))))
        pos = hero.get("position", [0.5, 0.44])
        hero["position"] = [float(pos[0]), float(pos[1])]
        hero["rotation_deg"] = float(hero.get("rotation_deg", 0))

        sec = data.get("secondary_element", {})
        sec["name"] = sec.get("name", "vintage secondary object")
        sec["prompt"] = sec.get("prompt", sec["name"])
        sec["scale"] = max(0.22, min(0.38, float(sec.get("scale", 0.32))))
        sec_pos = sec.get("position", [0.5, 0.72])
        sec["position"] = [float(sec_pos[0]), float(sec_pos[1])]
        sec["rotation_deg"] = float(sec.get("rotation_deg", 0))

        data["interaction_type"] = data.get("interaction_type", "EXAMINING")
        data["environment_graphic"] = data.get("environment_graphic", "microscope_reticle")
        data["has_pointing_hand"] = bool(data.get("has_pointing_hand", False))

        return data

    def _heuristic_fallback(self, sentence: str, topic_context: str, scene_idx: int) -> Dict[str, Any]:
        """Quy tắc heuristic phân tích cú pháp câu khi LLM bận."""
        s = (sentence + " " + topic_context).lower()

        if any(w in s for w in ["bạch cầu", "tế bào", "vi khuẩn", "kính hiển vi", "sinh học", "petri"]):
            archetype = "specimen_scientific"
            colors = self.ARCHETYPE_COLORS[archetype]
            color_item = colors[scene_idx % len(colors)]

            if "bạch cầu" in s or "thực bào" in s:
                hero_name = "giant glowing white blood cell warrior"
                hero_prompt = "a giant glowing white blood cell warrior"
                sec_name = "red bacteria colonies"
                sec_prompt = "red microscopic bacteria cells being engulfed"
                interaction = "ENGULFING"
                env = "microscope_reticle"
                hero_pos = [0.5, 0.44]
                sec_pos = [0.52, 0.68]
            else:
                hero_name = "vintage brass microscope"
                hero_prompt = "a vintage brass microscope"
                sec_name = "red bacteria petri dish"
                sec_prompt = "a glass petri dish with red bacteria colonies"
                interaction = "EXAMINING"
                env = "microscope_reticle"
                hero_pos = [0.5, 0.42]
                sec_pos = [0.5, 0.72]

        elif any(w in s for w in ["rãnh", "mariana", "biển", "đại dương", "tàu ngầm", "áp suất", "đo sâu"]):
            archetype = "geography_ocean"
            colors = self.ARCHETYPE_COLORS[archetype]
            color_item = colors[scene_idx % len(colors)]

            if "áp suất" in s:
                hero_name = "vintage industrial pressure gauge manometer"
                hero_prompt = "a vintage industrial pressure gauge manometer"
                sec_name = "yellow retro research submarine"
                sec_prompt = "a yellow retro research submarine"
                interaction = "PRESSING"
                env = "coordinate_grid"
                hero_pos = [0.5, 0.40]
                sec_pos = [0.5, 0.68]
            elif "phát quang" in s or "sinh vật" in s:
                hero_name = "bioluminescent anglerfish"
                hero_prompt = "a glowing deep-sea anglerfish"
                sec_name = "deep ocean scientific camera"
                sec_prompt = "a vintage deep-sea underwater exploration camera"
                interaction = "EXAMINING"
                env = "depth_contours"
                hero_pos = [0.5, 0.45]
                sec_pos = [0.5, 0.74]
            else:
                hero_name = "vintage research bathyscaphe submarine"
                hero_prompt = "a yellow retro research submarine"
                sec_name = "heavy cast iron ship anchor"
                sec_prompt = "a vintage nautical iron ship anchor"
                interaction = "MEASURING"
                env = "coordinate_grid"
                hero_pos = [0.5, 0.45]
                sec_pos = [0.5, 0.72]

        elif any(w in s for w in ["ai cập", "pharaoh", "ướp xác", "canopic", "cổ đại", "sarcophagus"]):
            archetype = "historical_relic"
            colors = self.ARCHETYPE_COLORS[archetype]
            color_item = colors[scene_idx % len(colors)]

            if "canopic" in s or "nội tạng" in s:
                hero_name = "ancient Egyptian canopic jar"
                hero_prompt = "an ancient Egyptian canopic jar"
                sec_name = "ancient papyrus manuscript scroll"
                sec_prompt = "an antique Egyptian papyrus scroll with hieroglyphs"
                interaction = "POINTING"
                env = "papyrus_frame"
                hero_pos = [0.5, 0.44]
                sec_pos = [0.5, 0.74]
                has_hand = True
            else:
                hero_name = "ornate gilded pharaoh sarcophagus"
                hero_prompt = "an ornate gilded ancient Egyptian pharaoh sarcophagus"
                sec_name = "ancient canopic jar"
                sec_prompt = "an ancient Egyptian alabaster canopic jar"
                interaction = "MEASURING"
                env = "papyrus_frame"
                hero_pos = [0.5, 0.45]
                sec_pos = [0.5, 0.73]
                has_hand = False
            return {
                "archetype": archetype,
                "color_field": color_item["name"],
                "color_hex": color_item["hex"],
                "interaction_type": interaction,
                "hero_element": {
                    "name": hero_name,
                    "prompt": hero_prompt,
                    "scale": 0.52,
                    "position": hero_pos,
                    "rotation_deg": -3
                },
                "secondary_element": {
                    "name": sec_name,
                    "prompt": sec_prompt,
                    "scale": 0.32,
                    "position": sec_pos,
                    "rotation_deg": 4
                },
                "environment_graphic": env,
                "has_pointing_hand": has_hand
            }

        else:  # Mechanic / Industrial
            archetype = "industrial_social"
            colors = self.ARCHETYPE_COLORS[archetype]
            color_item = colors[scene_idx % len(colors)]

            hero_name = "mechanical metal press machine"
            hero_prompt = "a mechanical orange juice citrus squeezer"
            sec_name = "fresh cut orange half"
            sec_prompt = "a fresh juicy cut orange half with pulp and droplets"
            interaction = "PRESSING"
            env = "ruler_scale"
            hero_pos = [0.5, 0.40]
            sec_pos = [0.5, 0.70]

        return {
            "archetype": archetype,
            "color_field": color_item["name"],
            "color_hex": color_item["hex"],
            "interaction_type": interaction,
            "hero_element": {
                "name": hero_name,
                "prompt": hero_prompt,
                "scale": 0.54,
                "position": hero_pos,
                "rotation_deg": -2
            },
            "secondary_element": {
                "name": sec_name,
                "prompt": sec_prompt,
                "scale": 0.32,
                "position": sec_pos,
                "rotation_deg": 3
            },
            "environment_graphic": env,
            "has_pointing_hand": (scene_idx % 2 == 1)
        }

    # Backward compatibility alias
    async def analyze_sentence(self, sentence: str, topic_context: str = "", scene_idx: int = 0) -> Dict[str, Any]:
        """Tương thích ngược với interface Phase 1."""
        layout = await self.design_scene(sentence, topic_context, scene_idx)
        hero = layout["hero_element"]["prompt"]
        sec = layout["secondary_element"]["prompt"]
        env = layout["environment_graphic"]
        color_field = layout["color_field"]

        flux_prompt = (
            f"An editorial surreal paper-collage illustration in vertical 9:16 composition: "
            f"{hero} interacting with {sec}, set against {env}, isolated on solid clean {color_field} cardstock background, "
            f"black and white halftone photographic textures, crisp cut paper edges, thin cream keylines, physical drop shadows."
        )

        return {
            "archetype": layout["archetype"],
            "hero_concept": hero,
            "dynamics": f"{layout['interaction_type']} {sec}",
            "grounding": env,
            "color_field": color_field,
            "color_hex": layout["color_hex"],
            "flux_prompt": flux_prompt,
            "scene_layout": layout
        }


# Alias class name
TextVisualAnalyzer = MultiElementSceneDesigner
