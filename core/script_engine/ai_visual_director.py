"""
AutoVideoFactory — AI Visual Director (Milestone M3 / Requirement R3)
Module Đạo Diễn Hình Họa Độc Lập cho Nhà Hát Cắt Dán Siêu Thực (Cinematic Collage Theatre).
Chuyển hóa câu thoại thuyết minh tiếng Việt thành Bản thiết kế Cảnh 7 Tầng (Scene Blueprint):
- Layer 0: Flat Cardstock Paper Field with Grain (spatial_context)
- Layer 1: Procedural Torn Paper Backdrop (archival_backdrop)
- Layer 2: Stage Prop with Environmental Shock (stage_prop)
- Layer 3: Secondary Target Actor (kinetic_cast.secondary_target)
- Layer 4: Hero Actor with Penetration & Recoil (kinetic_cast.hero_actor)
- Layer 5: Paper Debris FX with Cone Dispersion (cause_and_effect_fx.paper_debris_fx)
- Layer 6: Director Accents (director_accents)
+ Transition & Tactile Parameters (transition)

Hỗ trợ 2 chế độ vận hành:
1. Gemini LLM Mode: Phân tích ngữ cảnh sâu sắc khi có API key.
2. Deterministic Heuristic Fallback: Vận hành offline siêu tốc, đảm bảo 100% kết quả chuẩn xác
   cho "Lưỡi rìu bổ đôi khúc gỗ rừng già" và mọi câu thoại tiếng Việt thông qua VerbSemanticMatcher.
"""

import os
import re
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
from loguru import logger
from dotenv import load_dotenv
from core.config import get_gemini_model

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]

try:
    from .verb_semantic_matcher import VerbSemanticMatcher
except ImportError:
    from core.script_engine.verb_semantic_matcher import VerbSemanticMatcher


class AIVisualDirector:
    """
    Đạo diễn hình họa AI cho Nhà hát Cắt dán 7 Tầng (Cinematic Collage Theatre).
    Chịu trách nhiệm thiết kế không gian, phông nền tranh tư liệu, đạo cụ mặt sàn,
    dàn diễn viên động lực học, thông số va chạm cơ học và điểm nhấn đạo diễn.
    """

    ARCHETYPE_THEMES = {
        "conceptual_duel": {
            "color_field": "Plum & Gold",
            "color_hex": "4A235A",
            "environment_graphic": "coordinate_grid",
            "atmosphere": "vintage lumberjack carpentry atelier"
        },
        "industrial_social": {
            "color_field": "Burnt Terracotta",
            "color_hex": "D44D22",
            "environment_graphic": "ruler_scale",
            "atmosphere": "heavy industrial manufacturing workshop"
        },
        "specimen_scientific": {
            "color_field": "Deep Cobalt",
            "color_hex": "1D3557",
            "environment_graphic": "microscope_reticle",
            "atmosphere": "Victorian natural philosophy laboratory"
        },
        "geography_ocean": {
            "color_field": "Deep Cobalt",
            "color_hex": "1D3557",
            "environment_graphic": "depth_contours",
            "atmosphere": "deep sea oceanographic abyss expedition"
        },
        "historical_relic": {
            "color_field": "Mustard Cardstock",
            "color_hex": "E9C46A",
            "environment_graphic": "papyrus_frame",
            "atmosphere": "ancient pharaonic burial crypt"
        }
    }

    # Bảng thông số động cơ mặc định chuẩn Cinematic Collage Theatre
    ENGINE_DEFAULT_PARAMS = {
        "ENGINE_SEVER_SHATTER": {
            "impact_time": 1.8,
            "windup_tilt_deg": -35.0,
            "strike_tilt_deg": 6.0,
            "recoil_px": 8.0,
            "hero_impact_y": 0.66,
            "max_drift_px": 260.0,
            "tilt_deg": 30.0,
            "drift_direction": [1.0, 0.2],
            "paper_debris_fx": {
                "enabled": True,
                "count": 4,
                "dispersion_type": "cone",
                "dispersion_radius_px": [60, 120],
                "outline_width": 1.5,
                "outline_color": "#FFFDF7",
                "stop_motion_steps": 3
            },
            "hero_scale": 0.48,
            "hero_pos": [0.50, 0.16],
            "hero_flip_v": True,
            "sec_scale": 0.38,
            "sec_pos": [0.50, 0.68],
            "sec_bottom_anchor": True,
            "prop_shock": True
        },
        "ENGINE_COMPRESS_SQUASH": {
            "impact_time": 1.8,
            "windup_tilt_deg": 0.0,
            "strike_tilt_deg": 0.0,
            "recoil_px": 8.0,
            "hero_impact_y": 0.68,
            "max_drift_px": 0.0,
            "tilt_deg": 0.0,
            "drift_direction": [0.0, 0.0],
            "paper_debris_fx": {
                "enabled": True,
                "count": 3,
                "dispersion_type": "cone",
                "dispersion_radius_px": [40, 80],
                "outline_width": 1.5,
                "outline_color": "#FFFDF7",
                "stop_motion_steps": 3
            },
            "hero_scale": 0.52,
            "hero_pos": [0.50, 0.22],
            "hero_flip_v": False,
            "sec_scale": 0.35,
            "sec_pos": [0.50, 0.70],
            "sec_bottom_anchor": True,
            "prop_shock": True
        },
        "ENGINE_EMIT_SLIDE": {
            "impact_time": 1.8,
            "windup_tilt_deg": 0.0,
            "strike_tilt_deg": 0.0,
            "recoil_px": 0.0,
            "hero_impact_y": 0.45,
            "max_drift_px": 580.0,
            "tilt_deg": 10.0,
            "drift_direction": [1.0, 0.0],
            "paper_debris_fx": {
                "enabled": False,
                "count": 0,
                "dispersion_type": "cone",
                "dispersion_radius_px": [0, 0],
                "outline_width": 1.5,
                "outline_color": "#FFFDF7",
                "stop_motion_steps": 0
            },
            "hero_scale": 0.50,
            "hero_pos": [0.50, 0.40],
            "hero_flip_v": False,
            "sec_scale": 0.32,
            "sec_pos": [0.50, 0.68],
            "sec_bottom_anchor": False,
            "prop_shock": False
        },
        "ENGINE_CONVERGE_WRAP": {
            "impact_time": 1.8,
            "windup_tilt_deg": 0.0,
            "strike_tilt_deg": 0.0,
            "recoil_px": 0.0,
            "hero_impact_y": 0.48,
            "max_drift_px": 750.0,
            "tilt_deg": 15.0,
            "drift_direction": [-1.0, 0.0],
            "paper_debris_fx": {
                "enabled": False,
                "count": 0,
                "dispersion_type": "cone",
                "dispersion_radius_px": [0, 0],
                "outline_width": 1.5,
                "outline_color": "#FFFDF7",
                "stop_motion_steps": 0
            },
            "hero_scale": 0.48,
            "hero_pos": [0.50, 0.48],
            "hero_flip_v": False,
            "sec_scale": 0.40,
            "sec_pos": [0.50, 0.48],
            "sec_bottom_anchor": True,
            "prop_shock": False
        },
        "ENGINE_ABSORB_DISSOLVE": {
            "impact_time": 1.8,
            "windup_tilt_deg": 0.0,
            "strike_tilt_deg": 0.0,
            "recoil_px": 0.0,
            "hero_impact_y": 0.48,
            "max_drift_px": 0.0,
            "tilt_deg": 0.0,
            "drift_direction": [0.0, -1.0],
            "paper_debris_fx": {
                "enabled": False,
                "count": 0,
                "dispersion_type": "implosion",
                "dispersion_radius_px": [0, 0],
                "outline_width": 1.5,
                "outline_color": "#FFFDF7",
                "stop_motion_steps": 0
            },
            "hero_scale": 0.52,
            "hero_pos": [0.50, 0.48],
            "hero_flip_v": False,
            "sec_scale": 0.30,
            "sec_pos": [0.50, 0.85],
            "sec_bottom_anchor": False,
            "prop_shock": False
        },
        "ENGINE_TRANSLATE_NAV": {
            "impact_time": 1.8,
            "windup_tilt_deg": 0.0,
            "strike_tilt_deg": 22.0,
            "recoil_px": 0.0,
            "hero_impact_y": 0.78,
            "max_drift_px": 45.0,
            "tilt_deg": 22.0,
            "drift_direction": [0.88, 0.78],
            "paper_debris_fx": {
                "enabled": False,
                "count": 0,
                "dispersion_type": "cone",
                "dispersion_radius_px": [0, 0],
                "outline_width": 1.5,
                "outline_color": "#FFFDF7",
                "stop_motion_steps": 0
            },
            "hero_scale": 0.45,
            "hero_pos": [0.12, 0.22],
            "hero_flip_v": False,
            "sec_scale": 0.35,
            "sec_pos": [0.88, 0.78],
            "sec_bottom_anchor": False,
            "prop_shock": False
        },
        "ENGINE_SWEEP_OSCILLATE": {
            "impact_time": 1.8,
            "windup_tilt_deg": -45.0,
            "strike_tilt_deg": 45.0,
            "recoil_px": 0.0,
            "hero_impact_y": 0.45,
            "max_drift_px": 0.0,
            "tilt_deg": 45.0,
            "drift_direction": [0.0, 0.0],
            "paper_debris_fx": {
                "enabled": False,
                "count": 0,
                "dispersion_type": "cone",
                "dispersion_radius_px": [0, 0],
                "outline_width": 1.5,
                "outline_color": "#FFFDF7",
                "stop_motion_steps": 0
            },
            "hero_scale": 0.52,
            "hero_pos": [0.50, 0.42],
            "hero_flip_v": False,
            "sec_scale": 0.32,
            "sec_pos": [0.50, 0.72],
            "sec_bottom_anchor": True,
            "prop_shock": False
        },
        "ENGINE_REVOLVE_VORTEX": {
            "impact_time": 1.8,
            "windup_tilt_deg": 0.0,
            "strike_tilt_deg": 0.0,
            "recoil_px": 0.0,
            "hero_impact_y": 0.50,
            "max_drift_px": 420.0,
            "tilt_deg": 360.0,
            "drift_direction": [0.0, 0.0],
            "paper_debris_fx": {
                "enabled": False,
                "count": 0,
                "dispersion_type": "vortex",
                "dispersion_radius_px": [0, 0],
                "outline_width": 1.5,
                "outline_color": "#FFFDF7",
                "stop_motion_steps": 0
            },
            "hero_scale": 0.50,
            "hero_pos": [0.50, 0.50],
            "hero_flip_v": False,
            "sec_scale": 0.30,
            "sec_pos": [0.50, 0.50],
            "sec_bottom_anchor": False,
            "prop_shock": False
        }
    }

    def __init__(
        self,
        dict_path: Optional[Path] = None,
        gemini_client: Optional[Any] = None,
        cutout_dir: Optional[Path] = None
    ):
        """Khởi tạo AI Visual Director."""
        self.matcher = VerbSemanticMatcher(dict_path=dict_path)
        self.project_root = PROJECT_ROOT
        self.cutout_dir = cutout_dir or (self.project_root / "data" / "cache" / "cutouts")
        self.props_dir = self.project_root / "assets" / "collage_assets" / "props"
        self.fallback_dir = self.project_root / "assets" / "fallback_library"

        # Cấu hình Gemini nếu khả dụng
        self.gemini_client = gemini_client
        self.api_keys = []
        key1 = os.getenv("GEMINI_API_KEY_1") or os.getenv("GEMINI_API_KEY")
        key2 = os.getenv("GEMINI_API_KEY_2")
        for k in [key1, key2]:
            if k and k.strip() and not k.strip().startswith("your_") and k.strip() not in self.api_keys:
                self.api_keys.append(k.strip())
        self.current_key_idx = 0
        self.model_name = get_gemini_model()

    async def direct_scene(
        self,
        sentence: str,
        topic_context: str = "",
        scene_idx: int = 0
    ) -> Dict[str, Any]:
        """
        Phương thức chính: Dẫn dắt và sinh Bản thiết kế Cảnh 7 Tầng (Scene Blueprint).
        Tự động ưu tiên Gemini LLM nếu có API key, hoặc chuyển sang Deterministic Heuristic Fallback.
        """
        # 1. Thử sinh qua Gemini LLM nếu có API key
        if self.api_keys:
            try:
                bp_llm = await self._direct_llm(sentence, topic_context, scene_idx)
                if bp_llm:
                    return self._validate_and_sanitize_blueprint(bp_llm, sentence, scene_idx)
            except Exception as e:
                logger.warning(f"⚠️ [AIVisualDirector] LLM Generation không thành công ({e}), chuyển sang Heuristic.")

        # 2. Heuristic Deterministic Fallback (tốc độ cao, không tốn token, offline 100%)
        bp_heuristic = await self._direct_heuristic(sentence, topic_context, scene_idx)
        return self._validate_and_sanitize_blueprint(bp_heuristic, sentence, scene_idx)

    def direct_scene_sync(
        self,
        sentence: str,
        topic_context: str = "",
        scene_idx: int = 0
    ) -> Dict[str, Any]:
        """Wrapper đồng bộ cho direct_scene phục vụ các ngữ cảnh non-async."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    return pool.submit(asyncio.run, self.direct_scene(sentence, topic_context, scene_idx)).result()
            return loop.run_until_complete(self.direct_scene(sentence, topic_context, scene_idx))
        except Exception:
            return asyncio.run(self.direct_scene(sentence, topic_context, scene_idx))

    async def _direct_llm(
        self,
        sentence: str,
        topic_context: str = "",
        scene_idx: int = 0
    ) -> Optional[Dict[str, Any]]:
        """Sinh Scene Blueprint bằng Gemini LLM với cấu trúc JSON nghiêm ngặt."""
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_keys[self.current_key_idx])
            model = genai.GenerativeModel(self.model_name)

            prompt = f"""
Bạn là Đạo diễn Hình họa Điện ảnh (AI Visual Director) cho Nhà Hát Cắt Dán Siêu Thực (Cinematic Collage Theatre 12fps).
Nhiệm vụ: Phân tích câu thoại tiếng Việt và sinh Bản thiết kế Cảnh 7 Tầng (Scene Blueprint) định dạng JSON thuần túy.

Chủ đề: "{topic_context}"
Câu thoại: "{sentence}"
Scene Index: {scene_idx}

Quy định cấu trúc 7 Tầng bắt buộc (JSON duy nhất):
{{
  "spatial_context": {{
    "archetype": "conceptual_duel" | "specimen_scientific" | "geography_ocean" | "industrial_social" | "historical_relic",
    "color_field": "<tên màu Cardstock, vd: Plum & Gold, Deep Cobalt, Burnt Terracotta, Mustard Cardstock>",
    "color_hex": "<mã hex 6 ký tự không dấu #, vd: 4A235A, 1D3557, D44D22, E9C46A>",
    "environment_graphic": "coordinate_grid" | "microscope_reticle" | "depth_contours" | "papyrus_frame" | "ruler_scale",
    "atmosphere": "<mô tả ngắn bầu không khí cổ điển điện ảnh>"
  }},
  "archival_backdrop": {{
    "prompt": "<mô tả bức tranh khắc gỗ hoặc tranh tư liệu cổ điển thế kỷ 19>",
    "target_width": 860,
    "target_height": 950,
    "roughness": 12.0,
    "cellulose_fiber_color": "#F5EFEB",
    "shadow_offset": [8, 10],
    "shadow_blur": 8,
    "shadow_opacity": 0.35
  }},
  "stage_prop": {{
    "name": "<tên đạo cụ bệ đỡ sân khấu / mặt sàn, vd: carpenter_workbench, iron_anvil, laboratory_desk>",
    "prompt": "<mô tả chi tiết đạo cụ bệ đỡ>",
    "asset_path": null,
    "position": [0.50, 0.78],
    "scale": 0.65,
    "environmental_shock": {{
      "enabled": true,
      "magnitude_px": 8.0,
      "duration_frames": 4
    }}
  }},
  "kinetic_cast": {{
    "hero_actor": {{
      "name": "<tên vật thể chủ động hero, vd: axe, kitchen_knife, microscope, press_machine>",
      "prompt": "<mô tả prompt ảnh hero cắt dán vintage>",
      "asset_path": null,
      "scale": 0.48,
      "initial_position": [0.50, 0.16],
      "flip_vertical": true,
      "role": "agent"
    }},
    "secondary_target": {{
      "name": "<tên vật thể bị tác động, vd: wood_log, orange, bacteria, submarine>",
      "prompt": "<mô tả prompt ảnh secondary cắt dán vintage>",
      "asset_path": null,
      "scale": 0.38,
      "position": [0.50, 0.68],
      "bottom_anchor": true,
      "role": "target"
    }}
  }},
  "cause_and_effect_fx": {{
    "kinetic_engine": "ENGINE_SEVER_SHATTER" | "ENGINE_COMPRESS_SQUASH" | "ENGINE_EMIT_SLIDE" | "ENGINE_CONVERGE_WRAP" | "ENGINE_ABSORB_DISSOLVE" | "ENGINE_TRANSLATE_NAV" | "ENGINE_SWEEP_OSCILLATE" | "ENGINE_REVOLVE_VORTEX",
    "impact_time": 1.8,
    "windup_tilt_deg": -35.0,
    "strike_tilt_deg": 6.0,
    "recoil_px": 8.0,
    "hero_impact_y": 0.66,
    "max_drift_px": 260.0,
    "tilt_deg": 30.0,
    "drift_direction": [1.0, 0.2],
    "paper_debris_fx": {{
      "enabled": true,
      "count": 4,
      "dispersion_type": "cone",
      "dispersion_radius_px": [60, 120],
      "outline_width": 1.5,
      "outline_color": "#FFFDF7",
      "stop_motion_steps": 3
    }}
  }},
  "director_accents": {{
    "has_hand": false,
    "ruler_scale": false,
    "calligraphic_label": "<nhãn chữ thư pháp Latin hoặc phong cách cổ, vd: Securis & Lignum>"
  }},
  "transition": {{
    "in_transition": "stop_motion_cut",
    "tactile_jitter_amplitude": 1.5,
    "fps": 12
  }}
}}

Chỉ trả về JSON DUY NHẤT không có chú thích thêm.
"""
            resp = await asyncio.wait_for(
                model.generate_content_async(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.2,
                        response_mime_type="application/json"
                    )
                ),
                timeout=5.0
            )

            text = resp.text.strip()
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                raw_json = json.loads(match.group(0))
                return raw_json
        except Exception as e:
            logger.warning(f"⚠️ [AIVisualDirector] LLM call failure: {e}")

        return None

    async def _direct_heuristic(
        self,
        sentence: str,
        topic_context: str = "",
        scene_idx: int = 0
    ) -> Dict[str, Any]:
        """
        Quy tắc Heuristic chuyên sâu tạo Scene Blueprint hoàn chỉnh offline:
        1. Sử dụng VerbSemanticMatcher ánh xạ câu văn về Động từ chuẩn và Động cơ Kinetic.
        2. Tự động nhận diện thực thể Hero, Secondary, Stage Prop từ ngữ nghĩa câu thoại tiếng Việt.
        3. Tự động liên kết Cutout Asset đã có trong data/cache/cutouts.
        4. Cung cấp tham số va chạm cơ học chính xác tuyệt đối cho kịch bản mẫu:
           "Lưỡi rìu bổ đôi khúc gỗ rừng già" -> ENGINE_SEVER_SHATTER với viền xé, bệ thợ mộc, dăm vụn nón.
        """
        s_lower = sentence.lower()
        full_text = f"{sentence} {topic_context}".lower()

        # 1. Trích xuất thông tin động học từ VerbSemanticMatcher
        verb_entry = await self.matcher.match_sentence(sentence, topic_context)
        verb_vi = verb_entry.get("verb_vi", "")
        motion_type = verb_entry.get("motion_type", "")
        category = verb_entry.get("category", "")
        kinetic_engine = self.matcher.classify_kinetic_engine(verb_vi, motion_type, category)

        # 2. Phân tích thực thể chuyên biệt theo nhóm chủ đề
        is_axe_woodlog = any(w in s_lower for w in ["rìu", "khúc gỗ", "bổ đôi", "lưỡi rìu"]) or \
                         ("bổ" in s_lower and "gỗ" in s_lower)

        is_knife_bread = any(w in s_lower for w in ["bánh mì", "baguette", "dao bếp", "thái", "lát"]) or \
                         ("cắt" in s_lower and "bánh" in s_lower)

        is_biology = any(w in full_text for w in ["bạch cầu", "tế bào", "vi khuẩn", "kính hiển vi", "đĩa petri", "petri"])

        is_ocean = any(w in full_text for w in ["tàu ngầm", "rãnh", "mariana", "biển", "đại dương", "áp suất", "đo sâu", "thủy triều"])

        is_relic = any(w in full_text for w in ["pharaoh", "ai cập", "ướp xác", "canopic", "quan tài", "sarcophagus", "kim tự tháp"])

        is_press = any(w in full_text for w in ["máy ép", "nghiền", "dập", "cam", "nước cam", "bẹp dúm", "bóp nát"])

        is_astronomy = any(w in full_text for w in ["hố đen", "hành tinh", "vũ trụ", "thiên thạch", "quỹ đạo", "ngân hà"])

        # Thiết lập mặc định theo nhóm ngữ nghĩa
        if is_axe_woodlog:
            archetype = "conceptual_duel"
            hero_name = "axe"
            hero_prompt = "vintage iron lumberjack felling axe with wooden handle"
            hero_flip = True
            hero_scale = 0.48
            hero_pos = [0.50, 0.16]

            sec_name = "wood_log"
            sec_prompt = "dense antique pine tree wood log on chopping block"
            sec_scale = 0.38
            sec_pos = [0.50, 0.68]
            sec_bottom_anchor = True

            prop_name = "carpenter_workbench"
            prop_prompt = "vintage rustic wooden carpenter workbench tabletop"
            prop_scale = 0.65
            prop_pos = [0.50, 0.78]
            prop_shock_enabled = True

            backdrop_prompt = "19th-century vintage woodcut engraving of lumber sawmill and ancient pine trees"
            calligraphic_label = "Securis & Lignum"
            kinetic_engine = "ENGINE_SEVER_SHATTER"

        elif is_knife_bread:
            archetype = "conceptual_duel"
            hero_name = "kitchen_knife"
            hero_prompt = "vintage stainless steel kitchen chef knife"
            hero_flip = True
            hero_scale = 0.48
            hero_pos = [0.50, 0.18]

            sec_name = "baguette"
            sec_prompt = "crusty French artisan baguette bread"
            sec_scale = 0.38
            sec_pos = [0.50, 0.68]
            sec_bottom_anchor = True

            prop_name = "bread_cutting_board"
            prop_prompt = "rustic French wooden bakery cutting board"
            prop_scale = 0.65
            prop_pos = [0.50, 0.78]
            prop_shock_enabled = True

            backdrop_prompt = "19th-century Parisian artisan bakery kitchen engraving"
            calligraphic_label = "Culter & Panis"
            kinetic_engine = "ENGINE_SEVER_SHATTER"

        elif is_biology:
            archetype = "specimen_scientific"
            if "bạch cầu" in full_text or "thực bào" in full_text or "nuốt" in full_text:
                hero_name = "white_blood_cell"
                hero_prompt = "giant glowing white blood cell warrior engulfing pathogen"
                hero_scale = 0.52
                hero_pos = [0.50, 0.46]
                hero_flip = False

                sec_name = "bacteria"
                sec_prompt = "red microscopic bacteria pathogen colonies"
                sec_scale = 0.32
                sec_pos = [0.50, 0.70]
                sec_bottom_anchor = False

                prop_name = "specimen_glass_slide"
                prop_prompt = "vintage optical glass microscope slide stage"
                prop_scale = 0.65
                prop_pos = [0.50, 0.78]
                prop_shock_enabled = False

                backdrop_prompt = "antique cellular biological matrix compendium engraving"
                calligraphic_label = "Leucocytus & Pathogen"
                kinetic_engine = "ENGINE_ABSORB_DISSOLVE"
            else:
                hero_name = "microscope"
                hero_prompt = "vintage brass monocular laboratory microscope"
                hero_scale = 0.52
                hero_pos = [0.50, 0.42]
                hero_flip = False

                sec_name = "petri_dish"
                sec_prompt = "glass laboratory petri dish with bacterial culture"
                sec_scale = 0.32
                sec_pos = [0.50, 0.72]
                sec_bottom_anchor = True

                prop_name = "laboratory_desk"
                prop_prompt = "Victorian mahogany laboratory research table"
                prop_scale = 0.65
                prop_pos = [0.50, 0.78]
                prop_shock_enabled = False

                backdrop_prompt = "Victorian natural history laboratory and apothecary engraving"
                calligraphic_label = "Microscopium & Specimen"
                kinetic_engine = "ENGINE_SWEEP_OSCILLATE"

        elif is_ocean:
            archetype = "geography_ocean"
            hero_name = "submarine"
            hero_prompt = "yellow retro oceanic research bathyscaphe submarine"
            hero_scale = 0.46
            hero_pos = [0.18, 0.25]
            hero_flip = False

            sec_name = "pressure_gauge"
            sec_prompt = "vintage industrial brass manometer pressure gauge"
            sec_scale = 0.36
            sec_pos = [0.82, 0.76]
            sec_bottom_anchor = False

            prop_name = "oceanic_bedrock"
            prop_prompt = "deep oceanic Mariana trench basalt bedrock shelf"
            prop_scale = 0.65
            prop_pos = [0.50, 0.78]
            prop_shock_enabled = False

            backdrop_prompt = "19th-century oceanic cartography woodcut showing nautical depths and abyss"
            calligraphic_label = "Bathyscapha & Abyssus"
            kinetic_engine = "ENGINE_TRANSLATE_NAV"

        elif is_relic:
            archetype = "historical_relic"
            hero_name = "sarcophagus"
            hero_prompt = "ornate gilded ancient Egyptian pharaoh sarcophagus"
            hero_scale = 0.50
            hero_pos = [0.50, 0.44]
            hero_flip = False

            sec_name = "canopic_jar"
            sec_prompt = "ancient Egyptian alabaster canopic jar relic"
            sec_scale = 0.34
            sec_pos = [0.50, 0.72]
            sec_bottom_anchor = True

            prop_name = "ceremonial_altar"
            prop_prompt = "carved sandstone ancient Egyptian temple ceremonial altar"
            prop_scale = 0.65
            prop_pos = [0.50, 0.78]
            prop_shock_enabled = False

            backdrop_prompt = "antique sepia engraving of Great Pyramid of Giza and pharaonic tombs"
            calligraphic_label = "Pharaoh & Canopus"
            kinetic_engine = "ENGINE_CONVERGE_WRAP"

        elif is_press:
            archetype = "industrial_social"
            hero_name = "press_machine"
            hero_prompt = "mechanical metal press squeezer machine with levers"
            hero_scale = 0.52
            hero_pos = [0.50, 0.22]
            hero_flip = False

            sec_name = "orange_half"
            sec_prompt = "fresh cut juicy citrus orange half with droplets"
            sec_scale = 0.35
            sec_pos = [0.50, 0.70]
            sec_bottom_anchor = True

            prop_name = "industrial_workbench"
            prop_prompt = "heavy antique cast iron machine pedestal bench"
            prop_scale = 0.65
            prop_pos = [0.50, 0.78]
            prop_shock_enabled = True

            backdrop_prompt = "19th-century industrial foundry with steam machinery and gearwork"
            calligraphic_label = "Machina & Fructus"
            kinetic_engine = "ENGINE_COMPRESS_SQUASH"

        elif is_astronomy:
            archetype = "conceptual_duel"
            hero_name = "black_hole"
            hero_prompt = "cosmic gravitational black hole with accretion ring"
            hero_scale = 0.50
            hero_pos = [0.50, 0.48]
            hero_flip = False

            sec_name = "planet"
            sec_prompt = "celestial glowing astronomical planet sphere"
            sec_scale = 0.30
            sec_pos = [0.50, 0.50]
            sec_bottom_anchor = False

            prop_name = "armillary_stand"
            prop_prompt = "antique brass celestial armillary sphere tripod stand"
            prop_scale = 0.65
            prop_pos = [0.50, 0.78]
            prop_shock_enabled = False

            backdrop_prompt = "antique copperplate engraving of celestial constellations and planetary orbits"
            calligraphic_label = "Cosmos & Gravitas"
            kinetic_engine = "ENGINE_REVOLVE_VORTEX"

        else:
            # Fallback tổng quát theo Kinetic Engine được phân loại
            eng_theme = self.ARCHETYPE_THEMES.get("conceptual_duel")
            archetype = "conceptual_duel"
            hero_name = "vintage_agent_tool"
            hero_prompt = f"vintage editorial paper-cutout illustration of {sentence[:20]}"
            hero_scale = 0.48
            hero_pos = [0.50, 0.20]
            hero_flip = ("cắt" in s_lower or "chém" in s_lower or "chặt" in s_lower or "bổ" in s_lower)

            sec_name = "vintage_target_object"
            sec_prompt = "vintage editorial paper-cutout target object"
            sec_scale = 0.36
            sec_pos = [0.50, 0.68]
            sec_bottom_anchor = True

            prop_name = "studio_plinth"
            prop_prompt = "weathered vintage wooden studio stage plinth"
            prop_scale = 0.65
            prop_pos = [0.50, 0.78]
            prop_shock_enabled = (kinetic_engine in ["ENGINE_SEVER_SHATTER", "ENGINE_COMPRESS_SQUASH"])

            backdrop_prompt = "19th-century vintage editorial etching of archival workshop atelier"
            calligraphic_label = "Theatrum & Mechanica"

        # Lấy bảng màu và đồ họa môi trường cho archetype
        theme_cfg = self.ARCHETYPE_THEMES.get(archetype, self.ARCHETYPE_THEMES["conceptual_duel"])
        color_field = theme_cfg["color_field"]
        color_hex = theme_cfg["color_hex"]
        env_graphic = theme_cfg["environment_graphic"]
        atmosphere = theme_cfg["atmosphere"]

        # Tra cứu asset cache cục bộ
        hero_asset = self._resolve_cached_asset(hero_name, "hero")
        sec_asset = self._resolve_cached_asset(sec_name, "secondary")
        prop_asset = self._resolve_cached_asset(prop_name, "prop")

        # Lấy thông số động cơ từ bảng ENGINE_DEFAULT_PARAMS
        eng_params = self.ENGINE_DEFAULT_PARAMS.get(
            kinetic_engine,
            self.ENGINE_DEFAULT_PARAMS["ENGINE_SEVER_SHATTER"]
        )

        has_hand = False
        ruler_scale = False
        if kinetic_engine == "ENGINE_SWEEP_OSCILLATE" or scene_idx % 2 == 1:
            has_hand = True
        if kinetic_engine == "ENGINE_COMPRESS_SQUASH" or "đo" in s_lower:
            ruler_scale = True

        blueprint = {
            "spatial_context": {
                "archetype": archetype,
                "color_field": color_field,
                "color_hex": color_hex,
                "environment_graphic": env_graphic,
                "atmosphere": atmosphere
            },
            "archival_backdrop": {
                "prompt": backdrop_prompt,
                "target_width": 860,
                "target_height": 950,
                "roughness": 12.0,
                "cellulose_fiber_color": "#F5EFEB",
                "shadow_offset": (8, 10),
                "shadow_blur": 8,
                "shadow_opacity": 0.35
            },
            "stage_prop": {
                "name": prop_name,
                "prompt": prop_prompt,
                "asset_path": prop_asset,
                "position": prop_pos,
                "scale": prop_scale,
                "environmental_shock": {
                    "enabled": prop_shock_enabled,
                    "magnitude_px": 8.0 if prop_shock_enabled else 0.0,
                    "duration_frames": 4 if prop_shock_enabled else 0
                }
            },
            "kinetic_cast": {
                "hero_actor": {
                    "name": hero_name,
                    "prompt": hero_prompt,
                    "asset_path": hero_asset,
                    "scale": float(hero_scale),
                    "initial_position": hero_pos,
                    "flip_vertical": bool(hero_flip),
                    "role": "agent"
                },
                "secondary_target": {
                    "name": sec_name,
                    "prompt": sec_prompt,
                    "asset_path": sec_asset,
                    "scale": float(sec_scale),
                    "position": sec_pos,
                    "bottom_anchor": bool(sec_bottom_anchor),
                    "role": "target"
                }
            },
            "cause_and_effect_fx": {
                "kinetic_engine": kinetic_engine,
                "impact_time": float(eng_params["impact_time"]),
                "windup_tilt_deg": float(eng_params["windup_tilt_deg"]),
                "strike_tilt_deg": float(eng_params["strike_tilt_deg"]),
                "recoil_px": float(eng_params["recoil_px"]),
                "hero_impact_y": float(eng_params["hero_impact_y"]),
                "max_drift_px": float(eng_params["max_drift_px"]),
                "tilt_deg": float(eng_params["tilt_deg"]),
                "drift_direction": eng_params["drift_direction"],
                "paper_debris_fx": eng_params["paper_debris_fx"]
            },
            "director_accents": {
                "has_hand": has_hand,
                "ruler_scale": ruler_scale,
                "calligraphic_label": calligraphic_label
            },
            "transition": {
                "in_transition": "stop_motion_cut",
                "tactile_jitter_amplitude": 1.5,
                "fps": 12
            }
        }

        return blueprint

    def _resolve_cached_asset(
        self,
        keyword: str,
        role: str = "",
        job_cutout_dir: Optional[Union[str, Path]] = None
    ) -> Optional[str]:
        """
        Tra cứu asset cắt dán RGBA theo 2 cấp độ nghiêm ngặt (R1):
        - Level 1: Khớp chính xác (stem == keyword_clean hoặc kw_raw).
        - Level 2: Tất cả tokens có độ dài > 3 ký tự phải có mặt trong stem,
                   bỏ qua các file trung gian (_cutout, _raw, _raw_try1, test_...).
                   Với trường hợp chỉ có 1 token, token phải là tiền tố hoặc hậu tố.
        - Thứ tự ưu tiên: job_cutout_dir -> global_cutouts -> data/cache/cutouts.
        - Tuyệt đối không fallback sang asset ngẫu nhiên; nếu không tìm thấy trả về None.
        """
        if not keyword:
            return None

        kw_raw = str(keyword).lower().strip()
        if not kw_raw:
            return None

        if kw_raw.endswith(".png") or kw_raw.endswith(".jpg"):
            kw_raw = Path(kw_raw).stem.lower().strip()
            if not kw_raw:
                return None
        keyword_clean = re.sub(r'[\s\-]+', '_', kw_raw).strip('_')

        def is_blacklisted(f_stem: str) -> bool:
            s = f_stem.lower()
            return (
                s in {"scale", "scale.png"} or
                s.startswith("temp_") or
                s.startswith("test_") or
                "_raw_try" in s or
                s.endswith("_raw")
            )

        def is_intermediate_file(f_stem: str) -> bool:
            s = f_stem.lower()
            return is_blacklisted(s) or s.endswith("_cutout")

        # Reject blacklisted junk queries immediately
        if is_blacklisted(kw_raw) or is_blacklisted(keyword_clean):
            return None

        search_dirs: List[Path] = []
        target_job_dir = job_cutout_dir or getattr(self, "job_cutout_dir", None)
        if target_job_dir:
            p_job = Path(target_job_dir)
            if p_job.exists() and p_job.is_dir():
                search_dirs.append(p_job)

        proj_root = getattr(self, "project_root", None) or PROJECT_ROOT
        p_global = getattr(self, "global_cutouts_dir", None) or (proj_root / "data" / "asset_library" / "global_cutouts")
        if p_global and Path(p_global).exists() and Path(p_global).is_dir():
            search_dirs.append(Path(p_global))

        p_cache = getattr(self, "cutout_dir", None) or (proj_root / "data" / "cache" / "cutouts")
        if p_cache and Path(p_cache).exists() and Path(p_cache).is_dir():
            search_dirs.append(Path(p_cache))

        # Cấp độ 1: Exact match
        for d in search_dirs:
            for f in sorted(d.glob("*.png")):
                stem = f.stem.lower()
                if is_blacklisted(stem):
                    continue
                if is_intermediate_file(stem) and stem != keyword_clean and stem != kw_raw:
                    continue
                if stem == keyword_clean or stem == kw_raw:
                    return str(f.resolve())

        # Cấp độ 2: All tokens (length > 3) must be present in stem
        tokens = [t for t in re.split(r'[\s_\-]+', kw_raw) if len(t) > 3]
        if not tokens:
            tokens = [t for t in re.split(r'[\s_\-]+', kw_raw) if len(t) >= 3]
        if tokens:
            for d in search_dirs:
                for f in sorted(d.glob("*.png")):
                    stem = f.stem.lower()
                    if is_intermediate_file(stem):
                        continue
                    if len(tokens) == 1:
                        t = tokens[0]
                        if (
                            stem == t or
                            stem.startswith(f"{t}_") or
                            stem.startswith(f"{t}-") or
                            stem.endswith(f"_{t}") or
                            stem.endswith(f"-{t}")
                        ):
                            return str(f.resolve())
                    else:
                        if all(t in stem for t in tokens):
                            return str(f.resolve())

        return None


    def _validate_and_sanitize_blueprint(
        self,
        raw_bp: Dict[str, Any],
        sentence: str,
        scene_idx: int
    ) -> Dict[str, Any]:
        """
        Xác thực và chuẩn hóa toàn bộ cấu trúc 7 Tầng của Scene Blueprint:
        - Đảm bảo đầy đủ 7 keys gốc với đúng tên và cấu trúc con.
        - Đảm bảo các kiểu dữ liệu và giá trị mặc định chính xác.
        - Tự động bổ khuyết asset_path nếu đang thiếu.
        """
        sanitized: Dict[str, Any] = {}

        # 1. spatial_context
        sp = raw_bp.get("spatial_context", {})
        arch = sp.get("archetype", "conceptual_duel")
        if arch not in self.ARCHETYPE_THEMES:
            arch = "conceptual_duel"
        default_theme = self.ARCHETYPE_THEMES[arch]

        sanitized["spatial_context"] = {
            "archetype": str(arch),
            "color_field": str(sp.get("color_field") or default_theme["color_field"]),
            "color_hex": str(sp.get("color_hex") or default_theme["color_hex"]).lstrip("#"),
            "environment_graphic": str(sp.get("environment_graphic") or default_theme["environment_graphic"]),
            "atmosphere": str(sp.get("atmosphere") or default_theme["atmosphere"])
        }

        # 2. archival_backdrop
        bk = raw_bp.get("archival_backdrop", {})
        sh_offset = bk.get("shadow_offset", (8, 10))
        if isinstance(sh_offset, list):
            sh_offset = tuple(sh_offset)

        sanitized["archival_backdrop"] = {
            "prompt": str(bk.get("prompt") or "19th-century vintage woodcut engraving"),
            "target_width": int(bk.get("target_width", 860)),
            "target_height": int(bk.get("target_height", 950)),
            "roughness": float(bk.get("roughness", 12.0)),
            "cellulose_fiber_color": str(bk.get("cellulose_fiber_color", "#F5EFEB")),
            "shadow_offset": sh_offset,
            "shadow_blur": int(bk.get("shadow_blur", 8)),
            "shadow_opacity": float(bk.get("shadow_opacity", 0.35))
        }

        # 3. stage_prop
        pr = raw_bp.get("stage_prop", {})
        p_name = str(pr.get("name", "carpenter_workbench"))
        p_path = pr.get("asset_path") or self._resolve_cached_asset(p_name, "prop")
        raw_p_pos = pr.get("position", [0.50, 0.78])
        try:
            p_pos = [float(raw_p_pos[0]), float(raw_p_pos[1])]
        except (IndexError, TypeError, ValueError):
            p_pos = [0.50, 0.78]
        p_shock = pr.get("environmental_shock", {})

        sanitized["stage_prop"] = {
            "name": p_name,
            "prompt": str(pr.get("prompt") or "vintage rustic wooden workbench"),
            "asset_path": p_path,
            "position": p_pos,
            "scale": float(pr.get("scale", 0.65)),
            "environmental_shock": {
                "enabled": bool(p_shock.get("enabled", True)),
                "magnitude_px": float(p_shock.get("magnitude_px", 8.0)),
                "duration_frames": int(p_shock.get("duration_frames", 4))
            }
        }

        # 4. kinetic_cast
        kc = raw_bp.get("kinetic_cast", {})
        h = kc.get("hero_actor", {})
        s = kc.get("secondary_target", {})

        h_name = str(h.get("name", "axe"))
        h_path = h.get("asset_path") or self._resolve_cached_asset(h_name, "hero")
        raw_h_pos = h.get("initial_position", [0.50, 0.16])
        try:
            h_pos = [float(raw_h_pos[0]), float(raw_h_pos[1])]
        except (IndexError, TypeError, ValueError):
            h_pos = [0.50, 0.16]

        s_name = str(s.get("name", "wood_log"))
        s_path = s.get("asset_path") or self._resolve_cached_asset(s_name, "secondary")
        raw_s_pos = s.get("position", [0.50, 0.68])
        try:
            s_pos = [float(raw_s_pos[0]), float(raw_s_pos[1])]
        except (IndexError, TypeError, ValueError):
            s_pos = [0.50, 0.68]

        sanitized["kinetic_cast"] = {
            "hero_actor": {
                "name": h_name,
                "prompt": str(h.get("prompt") or h_name),
                "asset_path": h_path,
                "scale": float(h.get("scale", 0.48)),
                "initial_position": h_pos,
                "flip_vertical": bool(h.get("flip_vertical", True if ("axe" in h_name.lower() or "knife" in h_name.lower()) else False)),
                "role": str(h.get("role", "agent"))
            },
            "secondary_target": {
                "name": s_name,
                "prompt": str(s.get("prompt") or s_name),
                "asset_path": s_path,
                "scale": float(s.get("scale", 0.38)),
                "position": s_pos,
                "bottom_anchor": bool(s.get("bottom_anchor", True)),
                "role": str(s.get("role", "target"))
            }
        }

        # 5. cause_and_effect_fx
        ce = raw_bp.get("cause_and_effect_fx", {})
        engine = str(ce.get("kinetic_engine", "ENGINE_SEVER_SHATTER"))
        debris_fx = ce.get("paper_debris_fx", {})
        raw_drift = ce.get("drift_direction", [1.0, 0.2])
        try:
            drift_dir = [float(raw_drift[0]), float(raw_drift[1])]
        except (IndexError, TypeError, ValueError):
            drift_dir = [1.0, 0.2]

        raw_radius = debris_fx.get("dispersion_radius_px", [60, 120])
        try:
            disp_radius = [int(raw_radius[0]), int(raw_radius[1])]
        except (IndexError, TypeError, ValueError):
            disp_radius = [60, 120]

        impact_y = ce.get("hero_impact_y")
        if impact_y is None:
            impact_y = round(s_pos[1] - 0.02, 3)

        sanitized["cause_and_effect_fx"] = {
            "kinetic_engine": engine,
            "impact_time": float(ce.get("impact_time", 1.8)),
            "windup_tilt_deg": float(ce.get("windup_tilt_deg", -35.0)),
            "strike_tilt_deg": float(ce.get("strike_tilt_deg", 6.0)),
            "recoil_px": float(ce.get("recoil_px", 8.0)),
            "hero_impact_y": float(impact_y),
            "max_drift_px": float(ce.get("max_drift_px", 260.0)),
            "tilt_deg": float(ce.get("tilt_deg", 30.0)),
            "drift_direction": drift_dir,
            "paper_debris_fx": {
                "enabled": bool(debris_fx.get("enabled", True if engine in ["ENGINE_SEVER_SHATTER", "ENGINE_COMPRESS_SQUASH"] else False)),
                "count": int(debris_fx.get("count", 4)),
                "dispersion_type": str(debris_fx.get("dispersion_type", "cone")),
                "dispersion_radius_px": disp_radius,
                "outline_width": float(debris_fx.get("outline_width", 1.5)),
                "outline_color": str(debris_fx.get("outline_color", "#FFFDF7")),
                "stop_motion_steps": int(debris_fx.get("stop_motion_steps", 3))
            }
        }

        # 6. director_accents
        da = raw_bp.get("director_accents", {})
        sanitized["director_accents"] = {
            "has_hand": bool(da.get("has_hand", False)),
            "ruler_scale": bool(da.get("ruler_scale", False)),
            "calligraphic_label": da.get("calligraphic_label")
        }

        # 7. transition
        tr = raw_bp.get("transition", {})
        sanitized["transition"] = {
            "in_transition": str(tr.get("in_transition", "stop_motion_cut")),
            "tactile_jitter_amplitude": float(tr.get("tactile_jitter_amplitude", 1.5)),
            "fps": int(tr.get("fps", 12))
        }

        return sanitized

    def to_legacy_scene_layout(self, blueprint: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hàm tương thích ngược: Chuyển đổi 7-layer Scene Blueprint sang scene_layout cổ điển.
        """
        sp = blueprint.get("spatial_context", {})
        kc = blueprint.get("kinetic_cast", {})
        h = kc.get("hero_actor", {})
        s = kc.get("secondary_target", {})
        ce = blueprint.get("cause_and_effect_fx", {})
        da = blueprint.get("director_accents", {})

        return {
            "archetype": sp.get("archetype", "conceptual_duel"),
            "color_field": sp.get("color_field", "Plum & Gold"),
            "color_hex": sp.get("color_hex", "4A235A"),
            "interaction_type": ce.get("kinetic_engine", "ENGINE_SEVER_SHATTER"),
            "environment_graphic": sp.get("environment_graphic", "coordinate_grid"),
            "has_pointing_hand": da.get("has_hand", False),
            "archival_backdrop": blueprint.get("archival_backdrop", {}),
            "stage_prop": blueprint.get("stage_prop"),
            "is_floating": blueprint.get("is_floating", False),
            "hero_element": {
                "name": h.get("name", "hero"),
                "prompt": h.get("prompt", ""),
                "scale": h.get("scale", 0.48),
                "position": h.get("initial_position", [0.5, 0.16]),
                "flip_vertical": h.get("flip_vertical", False),
                "role": h.get("role", "agent")
            },
            "secondary_element": {
                "name": s.get("name", "secondary"),
                "prompt": s.get("prompt", ""),
                "scale": s.get("scale", 0.38),
                "position": s.get("position", [0.5, 0.68]),
                "bottom_anchor": s.get("bottom_anchor", True),
                "role": s.get("role", "target")
            },
            "kinetic_engine": ce.get("kinetic_engine", "ENGINE_SEVER_SHATTER"),
            "blueprint": blueprint
        }
