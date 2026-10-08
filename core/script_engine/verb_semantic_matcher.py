"""
AutoVideoFactory — Verb Semantic Matcher (Phase 2)
Module ánh xạ ngữ nghĩa 2 tầng giữa câu thoại tiếng Việt và 325 động từ chuẩn Kinetic:
- Tầng 1: Fast Exact & Synonym Match qua Inverted Index (tốc độ cao, không tốn token LLM).
- Tầng 2: LLM Lemma Fallback (Gemini) phân tích ẩn dụ, từ Hán-Việt hoặc từ hiếm gặp về 1 trong 325 động từ.
- Tự động đắp cấu trúc timeline, hero_behavior, target_reaction, action_assets vào scene_layout.
"""

import os
import re
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from loguru import logger
from dotenv import load_dotenv
from core.config import get_gemini_model

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DICT_PATH = PROJECT_ROOT / "data" / "dictionaries" / "verb_kinetic_dictionary.json"


class VerbSemanticMatcher:
    """
    Bộ ánh xạ ngữ nghĩa động từ tiếng Việt sang thông số động học stop-motion 12fps.
    """

    def __init__(self, dict_path: Optional[Path] = None):
        self.dict_path = Path(dict_path) if dict_path else DEFAULT_DICT_PATH
        self.dictionary: List[Dict[str, Any]] = []
        self.inverted_index: Dict[str, Dict[str, Any]] = {}
        self.sorted_phrases: List[Tuple[str, Dict[str, Any]]] = []

        self._load_dictionary()

        # Cấu hình Gemini cho Tầng 2
        self.api_keys = []
        key1 = os.getenv("GEMINI_API_KEY_1") or os.getenv("GEMINI_API_KEY")
        key2 = os.getenv("GEMINI_API_KEY_2")
        for k in [key1, key2]:
            if k and k.strip() and not k.strip().startswith("your_") and k.strip() not in self.api_keys:
                self.api_keys.append(k.strip())
        self.current_key_idx = 0
        self.model_name = get_gemini_model()

    def _load_dictionary(self):
        """Đọc từ điển JSON và xây dựng Inverted Index."""
        if not self.dict_path.exists():
            logger.error(f"❌ Không tìm thấy từ điển: {self.dict_path}")
            return

        with open(self.dict_path, "r", encoding="utf-8") as f:
            self.dictionary = json.load(f)

        # Xây dựng bảng tra cứu: map từ khóa -> entry
        for entry in self.dictionary:
            v_main = entry["verb_vi"].lower().strip()
            self.inverted_index[v_main] = entry

            for syn in entry.get("synonyms", []):
                syn_clean = syn.lower().strip()
                if syn_clean and syn_clean not in self.inverted_index:
                    self.inverted_index[syn_clean] = entry

        # Sắp xếp các cụm từ theo độ dài giảm dần (ưu tiên cụm từ nhiều chữ trước: "vươn xúc tu" > "vươn")
        all_phrases = [(phrase, entry) for phrase, entry in self.inverted_index.items()]
        self.sorted_phrases = sorted(all_phrases, key=lambda x: len(x[0]), reverse=True)

        logger.info(f"📖 [VerbSemanticMatcher] Đã nạp {len(self.dictionary)} động từ và {len(self.inverted_index)} cụm từ tra cứu.")

    def match_fast(self, sentence: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """
        Tầng 1: Quét cụm từ trong câu văn tiếng Việt (không tốn LLM token).
        Trả về: (matched_phrase, entry) hoặc None.
        """
        s_lower = sentence.lower()

        # Quét theo danh sách cụm từ đã sắp xếp giảm dần theo độ dài
        for phrase, entry in self.sorted_phrases:
            # Kiểm tra cụm từ có ranh giới từ hoặc xuất hiện rõ ràng trong câu
            pattern = r'(?:\b|\W|^)' + re.escape(phrase) + r'(?:\b|\W|$)'
            if re.search(pattern, s_lower):
                return phrase, entry

        return None

    async def match_llm(self, sentence: str, context: str = "") -> Dict[str, Any]:
        """
        Tầng 2: Sử dụng Gemini trích xuất động từ cốt lõi khi câu văn mang tính ẩn dụ hoặc từ ngữ hiếm.
        """
        if not self.api_keys:
            return self._heuristic_fallback(sentence)

        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_keys[self.current_key_idx])
            model = genai.GenerativeModel(self.model_name)

            prompt = f"""
Bạn là chuyên gia ngôn ngữ học tiếng Việt và đạo diễn chuyển động Stop-motion 12fps.
Nhiệm vụ: Tìm 1 ĐỘNG TỪ HÀNH ĐỘNG VẬT LÝ CỐT LÕI trong tiếng Việt tương đương nhất cho câu văn dưới đây.

Câu văn: "{sentence}"
Ngữ cảnh: "{context}"

Chọn 1 động từ vật lý chính xác nhất từ các nhóm sau:
- Nhóm 1 (Lực & Biến dạng): ép, nén, dập, nghiền, nghiền nát, bóp, cán, đập, nện, va chạm, cắt, xé, chém, chặt, bẻ, cưa, khoan, kéo, giật, xoắn, vặn, đâm, chọc, xuyên, cắn, phá hủy, san phẳng, vỡ vụn, sụt lún...
- Nhóm 2 (Sinh & Lan tỏa): in ấn, in, đóng dấu, xổ ảnh, phát sóng, truyền tin, phát tín hiệu, chiếu sáng, rọi, lóe sáng, phát quang, bắn, phóng, phun, phun trào, tràn, nổ tung, thổi, rải, gieo, sinh sản, đẻ, nở, nảy mầm, phân bào, tiết dịch, lây lan, ban chiếu, dấy binh...
- Nhóm 3 (Di chuyển & Thám hiểm): chạy, đi, bò, trườn, nhảy, lướt, trượt, lăn, rơi, rơi tự do, đáp, hạ cánh, bay, lượn, bơi, lặn, lặn sâu, chìm, nổi, trôi dạt, chảy, tuôn chảy, xoáy, sóng xô, ngập, xói mòn, sạt lở, quay quanh, quỹ đạo, hút vào, va chạm thiên thạch, di cư, săn mồi, thâm nhập, hành quân, tiến công, viễn chinh, thám hiểm, đổ bộ...
- Nhóm 4 (Quan sát & Lắp ráp): soi, chiếu, quét, ngắm, nhìn, quan sát, theo dõi, đo, đo đạc, cân, phóng to, thu nhỏ, giải mã, phân tích, định vị, kiểm tra, nghiệm thu, đốt cháy, cháy, đun sôi, đóng băng, tan chảy, kết tinh, phân hủy, rỉ sét, hóa thạch, tiến hóa, xây dựng, lắp ráp, ghép, đúc, điêu khắc, ướp xác, quấn băng, đặt vào quan tài, phong ấn, khai quật, vươn xúc tu, bao vây, bao bọc, nuốt chửng, giam cầm, phong tỏa, đối đầu, giao chiến...

Trả về định dạng JSON DUY NHẤT:
{{"core_verb": "<từ tiếng Việt được chọn>", "reason": "<giải thích ngắn>"}}
"""
            resp = await asyncio.wait_for(
                model.generate_content_async(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.2,
                        response_mime_type="application/json"
                    )
                ),
                timeout=4.0
            )

            text = resp.text.strip()
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                res_data = json.loads(match.group(0))
                core_v = res_data.get("core_verb", "").lower().strip()

                # Tra từ khóa do LLM gợi ý trong từ điển
                if core_v in self.inverted_index:
                    return self.inverted_index[core_v]

                # Quét từng từ trong inverted index
                for phrase, entry in self.sorted_phrases:
                    if phrase in core_v or core_v in phrase:
                        return entry

        except Exception as e:
            logger.warning(f"⚠️ [VerbSemanticMatcher] LLM fallback error ({e}), chuyển sang Heuristic.")

        return self._heuristic_fallback(sentence)

    def _heuristic_fallback(self, sentence: str) -> Dict[str, Any]:
        """Quy tắc heuristic phân loại dự phòng đảm bảo luôn có kết quả hợp lệ."""
        s = sentence.lower()

        # Nhóm 1: Lực & Biến dạng
        if any(w in s for w in ["sụp đổ", "tan hoang", "nghiền", "bẹp", "nát", "vỡ", "đập", "ép", "dập", "chém", "cắt"]):
            if "sụp đổ" in s:
                return self.inverted_index.get("san phẳng", self.dictionary[0])
            return self.inverted_index.get("nghiền nát", self.inverted_index.get("ép", self.dictionary[0]))

        # Nhóm 2: Sinh & Lan tỏa
        if any(w in s for w in ["phun", "bắn", "cháy rực", "sóng", "in", "lan", "sinh", "chiếu", "sáng"]):
            return self.inverted_index.get("phun trào", self.inverted_index.get("in", self.dictionary[85]))

        # Nhóm 3: Di chuyển
        if any(w in s for w in ["lặn", "bay", "chạy", "hành quân", "chìm", "trôi", "xoáy", "quay"]):
            return self.inverted_index.get("lặn sâu", self.inverted_index.get("hành quân", self.dictionary[165]))

        # Nhóm 4: Quan sát, Nghi lễ, Vây bắt
        if any(w in s for w in ["xúc tu", "vây", "nuốt", "xác", "quan tài", "soi", "đo", "khám"]):
            return self.inverted_index.get("bao vây", self.inverted_index.get("soi", self.dictionary[240]))

        # Mặc định lấy từ đầu tiên của nhóm 1
        return self.dictionary[0]

    async def match_sentence(self, sentence: str, context: str = "") -> Dict[str, Any]:
        """
        Hàm trung tâm: Ánh xạ câu thoại tiếng Việt sang mục từ từ điển chuẩn.
        - Tầng 1: Thử Fast Exact Match trước.
        - Tầng 2: Nếu chưa tìm thấy, kích hoạt LLM Lemma Fallback.
        """
        res_fast = self.match_fast(sentence)
        if res_fast:
            phrase, entry = res_fast
            logger.debug(f"⚡ [Fast Match O(1)] '{sentence[:30]}...' -> '{phrase}' ({entry['verb_vi']}) [{entry['category']}]")
            return entry

        # Tầng 2: LLM Lemma Fallback
        logger.info(f"🧠 [LLM Fallback] '{sentence[:35]}...' -> Phân tích ngữ nghĩa ẩn dụ...")
        entry_llm = await self.match_llm(sentence, context)
        return entry_llm

    def classify_kinetic_engine(self, verb_vi: str, motion_type: str, category: str) -> str:
        """
        Phân loại chính xác mục từ kịch bản về 1 trong 8 Động Cơ Chuyển Động Vật Lý Hoàn Chỉnh:
        1. ENGINE_COMPRESS_SQUASH
        2. ENGINE_SEVER_SHATTER
        3. ENGINE_EMIT_SLIDE
        4. ENGINE_CONVERGE_WRAP
        5. ENGINE_ABSORB_DISSOLVE
        6. ENGINE_TRANSLATE_NAV
        7. ENGINE_SWEEP_OSCILLATE
        8. ENGINE_REVOLVE_VORTEX
        """
        m = (motion_type or "").upper()
        v = (verb_vi or "").lower()

        # 8. Revolve & Vortex
        if m in ["ORBIT_REVOLVE", "PLANETARY_ROTATION", "KEPLERIAN_ORBIT", "GRAVITATIONAL_ATTRACT",
                "METEOR_IMPACT", "TORNADO_CYCLONE", "MAELSTROM_VORTEX", "BILLOW_CURL"] or \
           any(w in v for w in ["quay quanh", "quỹ đạo", "tự quay", "lốc xoáy", "xoáy nước"]):
            return "ENGINE_REVOLVE_VORTEX"

        # 7. Sweep & Oscillate
        if m in ["MICROSCOPE_INSPECT", "PROJECT_BEAM", "LIDAR_SCAN", "SWEEP_HORIZON", "AIM_SIGHT",
                "LOOK_GAZE", "OBSERVE_SCRUTINIZE", "TRACK_MONITOR", "SUPERVISE_OVERSEE", "GAUGE_MEASURE",
                "SURVEY_TRIANGULATE", "WEIGH_SCALE", "VOLUMETRIC_FLASK", "ENUMERATE_TALLY", "COMPUTE_SOLVE",
                "MAGNIFY_ZOOM", "MINIFY_SCALE_DOWN", "DECIPHER_DECODE", "ASSAY_ANALYZE", "DETECT_DISCOVER",
                "SCREEN_PROBE", "GEO_LOCATE", "AUDIT_VERIFY", "ACCEPTANCE_PASS", "INDEX_LOOKUP"] or \
           any(w in v for w in ["soi", "quét", "ngắm", "nhìn", "quan sát", "đo đạc", "cân", "giải mã", "tầm soát"]):
            return "ENGINE_SWEEP_OSCILLATE"

        # 5. Absorb & Dissolve
        if m in ["ENGULF_PHAGOCYTE", "BESIEGE_ENCIRCLE", "DECOMPOSE_DECAY", "ROT_PUTREFY", "PUTREFACTION",
                "FERMENTATION", "OXIDIZE_RUST", "OXIDATION_REACTION", "MELT_LIQUEFY", "EVAPORATE_VAPORIZE",
                "FUME_SMOLDER", "IGNITE_INCINERATE", "BURN_COMBUST", "KILN_SMELT", "CREMATE_BLAZE",
                "BOIL_EBULLITION", "FREEZE_SOLIDIFY", "CRYSTALLIZE", "CONGEAL_SET", "CONDENSE_PRECIPITATE",
                "SENESCENCE_AGE", "SUBSIDENCE_SINK", "SINK_FOUNDER", "EBB_RECEDE"] or \
           any(w in v for w in ["nuốt", "thực bào", "phân hủy", "tiêu biến", "tan chảy", "mục rữa", "chìm mất", "bốc hơi"]):
            return "ENGINE_ABSORB_DISSOLVE"

        # 4. Converge & Wrap
        if m in ["SWATHE_BANDAGE", "EMBALM_MUMMIFY", "ENTOMB_SARCOPHAGUS", "SEAL_CONSECRATE", "CONSTRUCT_BUILD",
                "ASSEMBLE_FIT", "MORTISE_TENON", "GLUE_AFFIX", "FASTEN_MOUNT", "MOUND_SCULPT", "CAST_MOLD",
                "SCULPT_CHISEL", "ENGRAVE_CARVE", "INTERMENT_BURY", "VENERATE_WORSHIP", "EXALT_GLORIFY",
                "CORONATION_CROWN", "ABDICATE_RELINQUISH", "SIGN_RATIFY", "ENVELOPE_WRAP", "BIND_TETHER",
                "INCARCERATE_IMPRISON", "CAGE_CONFINE", "BLOCKADE_SEAL", "CONFRONT_FACE", "SKIRMISH_CLASH",
                "RESIST_DEFEND", "REPEL_DRIVE_BACK", "STALEMATE_TUG", "OVERTHROW_TOPPLE"] or \
           any(w in v for w in ["quấn băng", "ướp xác", "quan tài", "phong ấn", "lắp ráp", "ghép", "bao bọc", "trói", "nhốt", "giam"]):
            return "ENGINE_CONVERGE_WRAP"

        # 2. Sever & Shatter
        if m in ["SHEAR_CUT", "TEAR_PULL", "BLADE_SLASH", "CLEAVE_CHOP", "SAW_SPLIT", "FRACTURE_BEND",
                "PLUCK_DETACH", "TRIM_DETAIL", "RAZOR_SLIT", "INCISION", "WEDGE_SPLIT", "SAW_RECIPROCATE",
                "PARE_PEEL", "NOTCH_GROOVE", "LATHE_TURN", "PLANE_SHAVE", "CHISEL_GOUGE", "DRILL_BORE",
                "BISECT_SPLIT", "SEPARATE_ISOLATE", "PIERCE_PUNCTURE", "POKE_PROD", "SKEWER_TRANSFIX",
                "PRICK_INJECT", "SYRINGE_INJECT", "PENETRATE_THROUGH", "PERFORATE_BREACH", "IMPLANT_STAKE",
                "LODGE_EMBED", "THREAD_SNAKE", "DISEMBOWEL_SHRED", "PULVERIZE_CRUSH", "DEMOLISH_DESTROY",
                "LEVEL_FLATTEN", "RAZE_GROUND", "FISSURE_RUPTURE", "DESICCATION_CRACK", "SHATTER_CRUMBLE",
                "BURST_EXPLODE"] or \
           any(w in v for w in ["cắt", "xé", "chém", "chặt", "xẻ", "bẻ", "cưa", "đục", "khoan", "vỡ vụn", "nứt toác", "đâm", "xuyên"]):
            return "ENGINE_SEVER_SHATTER"

        # 3. Emit & Slide
        if category == "EMISSION_SPAWNING" or m in ["EXTEND_TENTACLE"] or \
           any(w in v for w in ["in", "xổ", "sóng", "phun", "bắn", "bảo tử", "xúc tu", "tiết", "chiếu sáng", "phát"]):
            return "ENGINE_EMIT_SLIDE"

        # 6. Translate & Nav
        if category == "LOCOMOTION_NAVIGATION" or \
           any(w in v for w in ["chạy", "bò", "bay", "lặn", "bơi", "trôi", "hành quân", "thám hiểm", "viễn chinh", "đổ bộ"]):
            return "ENGINE_TRANSLATE_NAV"

        # 1. Compress & Squash (Mặc định cho nhóm lực ép)
        return "ENGINE_COMPRESS_SQUASH"

    def enrich_scene_layout(self, scene_layout: Dict[str, Any], sentence: str, verb_entry: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Đắp các thông số chuyển động vật lý từ 8 Universal Kinetic Engines vào scene_layout:
        - gán motion_type, category, verb_vi, kinetic_engine
        - tạo danh sách timeline cụ thể cho MotionTimelineEngine
        - đính kèm action_assets và tactile_impact
        """
        if not verb_entry:
            res = self.match_fast(sentence)
            verb_entry = res[1] if res else self._heuristic_fallback(sentence)

        category = verb_entry.get("category", "FORCE_DEFORMATION")
        motion_type = verb_entry.get("motion_type", "GENERIC_INTERACTION")
        verb_vi = verb_entry.get("verb_vi", "")
        hero_beh = verb_entry.get("hero_behavior", {})
        target_rec = verb_entry.get("target_reaction", {})
        tactile = verb_entry.get("tactile_impact", {})

        kinetic_engine = self.classify_kinetic_engine(verb_vi, motion_type, category)

        scene_layout["verb_vi"] = verb_vi
        scene_layout["category"] = category
        scene_layout["motion_type"] = motion_type
        scene_layout["kinetic_engine"] = kinetic_engine
        scene_layout["tactile_impact"] = tactile

        timeline_actions = []
        hero_cfg = scene_layout.get("hero_element", {})
        h_pos = hero_cfg.get("position", [0.5, 0.42])
        sec_cfg = scene_layout.get("secondary_element", {})
        s_pos = sec_cfg.get("position", [0.5, 0.70])

        # =====================================================================
        # 1. ENGINE_COMPRESS_SQUASH (Nén ép & Nghiền dẹp)
        # =====================================================================
        if kinetic_engine == "ENGINE_COMPRESS_SQUASH":
            timeline_actions.append({
                "target": "hero",
                "action": "DISCRETE_TRANSLATE",
                "time_range": [1.8, 2.5],
                "start_pos": h_pos,
                "end_pos": [h_pos[0], h_pos[1] + 0.12],
                "steps": 3
            })
            timeline_actions.append({
                "target": "secondary",
                "action": "ENGINE_COMPRESS_SQUASH",
                "time_range": [2.2, 2.8],
                "scale_x": 1.35,
                "scale_y": 0.55,
                "steps": 3
            })

        # =====================================================================
        # 2. ENGINE_SEVER_SHATTER (Cắt xẻ, Tách đôi & Vỡ vụn)
        # =====================================================================
        elif kinetic_engine == "ENGINE_SEVER_SHATTER":
            timeline_actions.append({
                "target": "hero",
                "action": "DISCRETE_TRANSLATE",
                "time_range": [1.6, 2.3],
                "start_pos": [h_pos[0] - 0.05, h_pos[1] - 0.08],
                "end_pos": [h_pos[0] + 0.04, h_pos[1] + 0.14],
                "steps": 2,
                "max_tilt_deg": -15.0
            })
            timeline_actions.append({
                "target": "secondary",
                "action": "ENGINE_SEVER_SHATTER",
                "impact_time": 2.1,
                "drift_direction": [1.0, 0.4],
                "max_drift_px": 160.0,
                "tilt_deg": 25.0,
                "duration": 0.8,
                "steps": 3
            })

        # =====================================================================
        # 3. ENGINE_EMIT_SLIDE (Đùn trượt liên tiếp từ trong ra ngoài)
        # =====================================================================
        elif kinetic_engine == "ENGINE_EMIT_SLIDE":
            action_assets = verb_entry.get("action_assets", [])
            if not action_assets:
                action_assets = [{"id": "slide_item_1", "description": "emitted item", "prompt": "vintage card", "scale": 0.28}]

            scene_layout["action_assets"] = []
            for i, act_asset in enumerate(action_assets):
                act_id = f"action_asset_{i+1}"
                scene_layout["action_assets"].append({
                    "id": act_id,
                    "description": act_asset.get("description", ""),
                    "prompt": act_asset.get("prompt", ""),
                    "scale": act_asset.get("scale", 0.28),
                    "layer_order": "below_hero"
                })
                spawn_t = 1.8 + i * 0.8
                timeline_actions.append({
                    "target": act_id,
                    "action": "ENGINE_EMIT_SLIDE",
                    "spawn_time": spawn_t,
                    "slide_direction": [0.0, 1.0],
                    "distance": 240.0 + i * 40.0,
                    "duration": 0.8,
                    "steps": 4
                })

        # =====================================================================
        # 4. ENGINE_CONVERGE_WRAP (Hội tụ, Bao bọc & Đóng gói từ ngoài vào)
        # =====================================================================
        elif kinetic_engine == "ENGINE_CONVERGE_WRAP":
            action_assets = verb_entry.get("action_assets", [])
            if not action_assets:
                action_assets = [{"id": "wrap_band_1", "description": "linen wrapping", "prompt": "linen band", "scale": 0.32}]

            scene_layout["action_assets"] = []
            for i, act_asset in enumerate(action_assets):
                act_id = f"action_asset_{i+1}"
                scene_layout["action_assets"].append({
                    "id": act_id,
                    "description": act_asset.get("description", ""),
                    "prompt": act_asset.get("prompt", ""),
                    "scale": act_asset.get("scale", 0.32),
                    "layer_order": "above_hero"
                })
                start_t = 1.6 + i * 0.6
                sign = 1.0 if (i % 2 == 0) else -1.0
                timeline_actions.append({
                    "target": act_id,
                    "action": "ENGINE_CONVERGE_WRAP",
                    "start_time": start_t,
                    "start_offset": [sign * 320.0, -180.0],
                    "duration": 0.9,
                    "steps": 4
                })

        # =====================================================================
        # 5. ENGINE_ABSORB_DISSOLVE (Nuốt chửng, Thực bào & Tiêu biến)
        # =====================================================================
        elif kinetic_engine == "ENGINE_ABSORB_DISSOLVE":
            timeline_actions.append({
                "target": "hero",
                "action": "SQUASH_AND_STRETCH",
                "time_range": [1.6, 2.5],
                "scale_x": 1.25,
                "scale_y": 1.25,
                "steps": 3
            })
            timeline_actions.append({
                "target": "secondary",
                "action": "ENGINE_ABSORB_DISSOLVE",
                "absorb_time": 2.0,
                "duration": 1.2,
                "steps": 4
            })

        # =====================================================================
        # 6. ENGINE_TRANSLATE_NAV (Tịnh tiến & Hành trình có góc lượn sóng)
        # =====================================================================
        elif kinetic_engine == "ENGINE_TRANSLATE_NAV":
            timeline_actions.append({
                "target": "hero",
                "action": "ENGINE_TRANSLATE_NAV",
                "time_range": [1.2, 3.6],
                "start_pos": [h_pos[0] - 0.15, h_pos[1] - 0.10],
                "end_pos": [h_pos[0] + 0.15, h_pos[1] + 0.15],
                "max_tilt_deg": 12.0,
                "steps": 5
            })

        # =====================================================================
        # 7. ENGINE_SWEEP_OSCILLATE (Soi quét dao động)
        # =====================================================================
        elif kinetic_engine == "ENGINE_SWEEP_OSCILLATE":
            timeline_actions.append({
                "target": "hero",
                "action": "ENGINE_SWEEP_OSCILLATE",
                "time_range": [1.2, 3.8],
                "sweep_angle": 22.0,
                "cycles": 2,
                "steps_per_cycle": 4
            })

        # =====================================================================
        # 8. ENGINE_REVOLVE_VORTEX (Quay quanh tâm & Lốc xoáy)
        # =====================================================================
        elif kinetic_engine == "ENGINE_REVOLVE_VORTEX":
            timeline_actions.append({
                "target": "secondary",
                "action": "ENGINE_REVOLVE_VORTEX",
                "center_pos": h_pos,
                "radius": 260.0,
                "time_range": [1.2, 4.2],
                "total_revolutions": 1.0,
                "steps": 8
            })

        scene_layout["timeline"] = timeline_actions
        return scene_layout


# ---------------------------------------------------------------------------
# Stage 6 — singleton + gợi ý beat_action cho story beats
# ---------------------------------------------------------------------------
_matcher_singleton = None
_matcher_init_tried = False


def get_matcher() -> Optional["VerbSemanticMatcher"]:
    """Singleton lười: nạp từ điển 1 lần, trả None khi từ điển lỗi/thiếu."""
    global _matcher_singleton, _matcher_init_tried
    if not _matcher_init_tried:
        _matcher_init_tried = True
        try:
            m = VerbSemanticMatcher()
            _matcher_singleton = m if m.dictionary else None
        except Exception as e:
            logger.warning(f"get_matcher: không nạp được từ điển động từ ({e})")
            _matcher_singleton = None
    return _matcher_singleton


def suggest_beat_action(narration_part: str) -> Optional[Dict[str, Any]]:
    """
    Gợi ý beat_action cho 1 cụm lời thoại từ từ điển động từ (tầng 1: khớp nhanh).
    Trả về {"phrase", "beat_action", "verb_vi", "category"} hoặc None.
    Chỉ gợi ý khi entry có beat_action (bỏ qua 320 động từ cơ khí cũ).
    """
    matcher = get_matcher()
    if matcher is None or not (narration_part or "").strip():
        return None
    hit = matcher.match_fast(narration_part)
    if not hit:
        return None
    phrase, entry = hit
    beat_action = str(entry.get("beat_action") or "").strip()
    if not beat_action:
        return None
    return {
        "phrase": phrase,
        "beat_action": beat_action,
        "verb_vi": entry.get("verb_vi", ""),
        "category": entry.get("category", ""),
    }
