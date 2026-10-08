"""
AutoVideoFactory — Build Verb Kinetic Dictionary (Phase 1)
Mã hóa đầy đủ 325 động từ tiếng Việt cốt lõi vào data/dictionaries/verb_kinetic_dictionary.json
theo 4 nhóm chuẩn động học stop-motion 12fps.
"""

import sys
import json
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DATA_DIR = Path("data/dictionaries")
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE = DATA_DIR / "verb_kinetic_dictionary.json"

# Định nghĩa dữ liệu chi tiết cho 325 từ
VERBS_DATA = []

def add_verb(verb_vi, synonyms, category, domain_tags, motion_type, hero_action, hero_dir, hero_steps, hero_easing,
             target_action, target_sx, target_sy, target_steps, target_delay, action_assets, shake_screen=True, shake_amp=1.5,
             beat_action=""):
    VERBS_DATA.append({
        "verb_vi": verb_vi,
        "synonyms": synonyms,
        "category": category,
        "domain_tags": domain_tags,
        "motion_type": motion_type,
        "hero_behavior": {
            "action": hero_action,
            "direction": hero_dir,
            "steps": hero_steps,
            "easing": hero_easing
        },
        "target_reaction": {
            "action": target_action,
            "scale_x": target_sx,
            "scale_y": target_sy,
            "steps": target_steps,
            "delay_sec": target_delay
        },
        "action_assets": action_assets,
        "tactile_impact": {
            "shake_screen": shake_screen,
            "shake_amplitude": shake_amp
        },
        "beat_action": beat_action,
    })

# ==============================================================================
# NHÓM 1: TÁC ĐỘNG LỰC & BIẾN DẠNG (Force & Deformation) — 85 ĐỘNG TỪ
# ==============================================================================

# 1. Ép, Nén, Nghiền (14 từ)
n1_ep = [
    ("ép", ["nén", "dập", "chèn ép"], "FORCE_DEFORMATION", ["mechanics", "industrial", "general"], "HEAVY_PRESS",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 3, "PHYSICAL_BOUNCE", "SQUASH_AND_STRETCH", 1.35, 0.65, 3, 0.25,
     [{"id": "juice_droplets", "description": "droplets and splatters", "prompt": "splashing liquid droplets cutout", "scale": 0.2}]),
    ("nén", ["ép", "nén chặt", "siết"], "FORCE_DEFORMATION", ["mechanics", "physics", "geography"], "COMPRESSION",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 4, "LINEAR_STEP", "SQUASH_AND_STRETCH", 1.3, 0.6, 3, 0.3, []),
    ("dập", ["nện", "ép dập", "đột dập"], "FORCE_DEFORMATION", ["mechanics", "industrial"], "STAMP_IMPACT",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 2, "PHYSICAL_BOUNCE", "SQUASH_AND_STRETCH", 1.4, 0.55, 3, 0.2, []),
    ("nghiền", ["xay", "nghiền nát", "nghiền vụn"], "FORCE_DEFORMATION", ["mechanics", "geology", "general"], "ROTARY_CRUSH",
     "SQUASH_AND_STRETCH", [0.0, 1.0], 3, "PHYSICAL_BOUNCE", "SPLIT_HALF", 1.25, 0.7, 3, 0.3,
     [{"id": "powder_dust", "description": "crushed powder dust particles", "prompt": "fine crushed powder dust particles", "scale": 0.22}]),
    ("bóp", ["siết", "nắm chặt", "bóp bẹp"], "FORCE_DEFORMATION", ["biology", "general"], "CONSTRICTION",
     "SQUASH_AND_STRETCH", [1.0, 0.0], 3, "LINEAR_STEP", "SQUASH_AND_STRETCH", 0.7, 1.25, 3, 0.2, []),
    ("giã", ["nện", "giã nhuyễn", "thúc"], "FORCE_DEFORMATION", ["culinary", "mechanics"], "PESTLE_STRIKE",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 3, "PHYSICAL_BOUNCE", "SQUASH_AND_STRETCH", 1.3, 0.65, 3, 0.2, []),
    ("xay", ["nghiền", "xay xát", "quay"], "FORCE_DEFORMATION", ["mechanics", "food_science"], "MILL_ROTATION",
     "SQUASH_AND_STRETCH", [0.0, 0.0], 4, "LINEAR_STEP", "FRAGMENT_BURST", 1.2, 0.8, 3, 0.35, []),
    ("cán", ["cán phẳng", "lăn", "là"], "FORCE_DEFORMATION", ["industrial", "metallurgy"], "ROLLER_FLATTEN",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 4, "LINEAR_STEP", "SQUASH_AND_STRETCH", 1.5, 0.5, 4, 0.2, []),
    ("nghiến", ["nghiến chặt", "kẹp chặt"], "FORCE_DEFORMATION", ["biology", "mechanics"], "JAW_CLAMP",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 3, "HOLD_JITTER", "SQUASH_AND_STRETCH", 1.2, 0.75, 3, 0.2, []),
    ("kẹp", ["giữ", "kẹp chặt", "gắp"], "FORCE_DEFORMATION", ["mechanics", "laboratory"], "PINCER_GRIP",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 3, "LINEAR_STEP", "SQUASH_AND_STRETCH", 0.8, 1.2, 3, 0.25, []),
    ("siết", ["vặn chặt", "buộc chặt", "thắt"], "FORCE_DEFORMATION", ["mechanics", "general"], "TIGHTEN",
     "SQUASH_AND_STRETCH", [0.0, 0.0], 3, "LINEAR_STEP", "SQUASH_AND_STRETCH", 0.85, 0.85, 3, 0.2, []),
    ("đè", ["đè lên", "nén xuống", "áp"], "FORCE_DEFORMATION", ["physics", "geography"], "OVERLAY_WEIGHT",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 3, "PHYSICAL_BOUNCE", "SQUASH_AND_STRETCH", 1.25, 0.7, 3, 0.3, []),
    ("bẹp", ["làm bẹp", "móp méo", "dẹp"], "FORCE_DEFORMATION", ["mechanics", "general"], "FLATTEN",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 2, "PHYSICAL_BOUNCE", "SQUASH_AND_STRETCH", 1.45, 0.5, 3, 0.15, []),
    ("nén ép", ["ép nén", "nén chặt"], "FORCE_DEFORMATION", ["mechanics", "physics"], "HYDRAULIC_PRESS",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 4, "PHYSICAL_BOUNCE", "SQUASH_AND_STRETCH", 1.35, 0.6, 3, 0.25, [])
]

# 2. Đập, Đóng, Đột dập (14 từ)
n1_dap = [
    ("đập", ["nện", "quất", "gõ"], "FORCE_DEFORMATION", ["mechanics", "general"], "HAMMER_SMASH",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 2, "PHYSICAL_BOUNCE", "CRACK", 1.2, 0.8, 2, 0.15,
     [{"id": "crack_marks", "description": "fracture crack lines", "prompt": "black crack fracture lines texture", "scale": 0.3}]),
    ("đóng", ["đóng đinh", "gõ cọc"], "FORCE_DEFORMATION", ["construction", "carpentry"], "NAIL_DRIVE",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 3, "PHYSICAL_BOUNCE", "SQUASH_AND_STRETCH", 1.1, 0.9, 3, 0.2, []),
    ("gõ", ["cốc", "nhịp", "gõ nhẹ"], "FORCE_DEFORMATION", ["general", "music"], "TAP_STRIKE",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 2, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.1, []),
    ("nện", ["giáng", "nện mạnh"], "FORCE_DEFORMATION", ["mechanics", "warfare"], "HEAVY_SLUG",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 2, "PHYSICAL_BOUNCE", "SQUASH_AND_STRETCH", 1.4, 0.6, 3, 0.15, []),
    ("quai", ["vung", "quai búa"], "FORCE_DEFORMATION", ["metallurgy", "smithing"], "SWING_STRIKE",
     "DISCRETE_TRANSLATE", [1.0, 1.0], 3, "PHYSICAL_BOUNCE", "SQUASH_AND_STRETCH", 1.25, 0.75, 3, 0.2,
     [{"id": "metal_sparks", "description": "glowing forge sparks", "prompt": "golden forge sparks flying", "scale": 0.25}]),
    ("quất", ["vụt", "đánh mạnh"], "FORCE_DEFORMATION", ["general", "nature"], "WHIP_LASH",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 2, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.1, []),
    ("vỗ", ["vỗ về", "đập nhẹ"], "FORCE_DEFORMATION", ["general", "biology"], "CLAP_PAT",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 2, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.1, []),
    ("đinh", ["đóng đinh", "ghim"], "FORCE_DEFORMATION", ["construction"], "STAKE_DRIVE",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 3, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.15, []),
    ("thúc", ["thúc mạnh", "huých"], "FORCE_DEFORMATION", ["general", "warfare"], "JAB_THRUST",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 2, "PHYSICAL_BOUNCE", "SQUASH_AND_STRETCH", 0.85, 1.15, 2, 0.15, []),
    ("húc", ["húc đầu", "đâm sầm"], "FORCE_DEFORMATION", ["biology", "zoology"], "RAM_CHARGE",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 3, "PHYSICAL_BOUNCE", "SQUASH_AND_STRETCH", 0.75, 1.25, 3, 0.2, []),
    ("va chạm", ["va đập", "đụng độ"], "FORCE_DEFORMATION", ["physics", "astronomy", "transport"], "COLLISION_IMPACT",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 3, "PHYSICAL_BOUNCE", "CRACK", 1.2, 0.8, 3, 0.2, []),
    ("va đập", ["đập vào", "va chạm mạnh"], "FORCE_DEFORMATION", ["physics", "marine"], "HARD_IMPACT",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 3, "PHYSICAL_BOUNCE", "SQUASH_AND_STRETCH", 1.3, 0.7, 3, 0.2, []),
    ("chèn", ["chèn ép", "kẹp giữa"], "FORCE_DEFORMATION", ["mechanics", "geography"], "WEDGE_JAM",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 3, "LINEAR_STEP", "SQUASH_AND_STRETCH", 1.2, 0.8, 3, 0.25, []),
    ("xô", ["xô đẩy", "đẩy mạnh"], "FORCE_DEFORMATION", ["general", "physics"], "SHOVE_DISPLACE",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 2, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 2, 0.15, [])
]

# 3. Cắt, Xé, Bẻ, Tách (20 từ)
n1_cat = [
    ("cắt", ["chém", "tỉa", "khía"], "FORCE_DEFORMATION", ["mechanics", "surgery", "general"], "SHEAR_CUT",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 2, "LINEAR_STEP", "SPLIT_HALF", 1.0, 1.0, 2, 0.2,
     [{"id": "cut_line", "description": "sharp cut line divider", "prompt": "clean sharp blade cut divider", "scale": 0.25}]),
    ("xé", ["xé rách", "xé toạc"], "FORCE_DEFORMATION", ["general", "biology"], "TEAR_PULL",
     "SQUASH_AND_STRETCH", [1.0, 0.0], 3, "PHYSICAL_BOUNCE", "SPLIT_HALF", 1.3, 0.8, 3, 0.2, []),
    ("chém", ["chặt", "vung kiếm"], "FORCE_DEFORMATION", ["history", "warfare"], "BLADE_SLASH",
     "DISCRETE_TRANSLATE", [1.0, 1.0], 2, "PHYSICAL_BOUNCE", "SPLIT_HALF", 1.0, 1.0, 2, 0.15, []),
    ("chặt", ["bổ", "đốn"], "FORCE_DEFORMATION", ["forestry", "general"], "CLEAVE_CHOP",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 2, "PHYSICAL_BOUNCE", "SPLIT_HALF", 1.1, 0.9, 2, 0.15, []),
    ("xẻ", ["bửa", "xẻ gỗ"], "FORCE_DEFORMATION", ["carpentry", "industrial"], "SAW_SPLIT",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 3, "LINEAR_STEP", "SPLIT_HALF", 1.1, 0.9, 3, 0.25, []),
    ("bẻ", ["bẻ gãy", "bẻ đôi"], "FORCE_DEFORMATION", ["general", "mechanics"], "FRACTURE_BEND",
     "SQUASH_AND_STRETCH", [0.0, 1.0], 3, "PHYSICAL_BOUNCE", "SPLIT_HALF", 1.15, 0.85, 2, 0.2, []),
    ("ngắt", ["bứt", "hái"], "FORCE_DEFORMATION", ["biology", "botany"], "PLUCK_DETACH",
     "DISCRETE_TRANSLATE", [0.0, -1.0], 2, "LINEAR_STEP", "SHRINK_AND_DISAPPEAR", 0.9, 0.9, 2, 0.15, []),
    ("tỉa", ["cắt tỉa", "gọt giũa"], "FORCE_DEFORMATION", ["botany", "craft"], "TRIM_DETAIL",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.2, []),
    ("rọc", ["rạch", "rọc giấy"], "FORCE_DEFORMATION", ["craft", "surgery"], "RAZOR_SLIT",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 3, "LINEAR_STEP", "SPLIT_HALF", 1.0, 1.0, 2, 0.2, []),
    ("rạch", ["khía", "rạch mổ"], "FORCE_DEFORMATION", ["surgery", "biology"], "INCISION",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 2, "LINEAR_STEP", "SPLIT_HALF", 1.05, 0.95, 2, 0.15, []),
    ("bửa", ["xẻ đôi", "bổ"], "FORCE_DEFORMATION", ["general", "agriculture"], "WEDGE_SPLIT",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 2, "PHYSICAL_BOUNCE", "SPLIT_HALF", 1.2, 0.8, 2, 0.2, []),
    ("cưa", ["xẻ cưa", "cắt cưa"], "FORCE_DEFORMATION", ["carpentry", "mechanics"], "SAW_RECIPROCATE",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 4, "LINEAR_STEP", "SPLIT_HALF", 1.0, 1.0, 3, 0.3,
     [{"id": "sawdust", "description": "flying sawdust particles", "prompt": "wood sawdust flakes flying", "scale": 0.2}]),
    ("gọt", ["bào", "tỉa vỏ"], "FORCE_DEFORMATION", ["craft", "culinary"], "PARE_PEEL",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 3, "LINEAR_STEP", "SQUASH_AND_STRETCH", 0.95, 0.95, 2, 0.2, []),
    ("khía", ["rạch nông", "khía rãnh"], "FORCE_DEFORMATION", ["mechanics", "craft"], "NOTCH_GROOVE",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 2, "LINEAR_STEP", "CRACK", 1.0, 1.0, 2, 0.15, []),
    ("tiện", ["tiện gọt", "tiện kim loại"], "FORCE_DEFORMATION", ["mechanics", "metallurgy"], "LATHE_TURN",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 2, 0.25, []),
    ("bào", ["bào mòn", "bào gỗ"], "FORCE_DEFORMATION", ["carpentry", "craft"], "PLANE_SHAVE",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 2, 0.2, []),
    ("đục", ["đục khoét", "đục đá"], "FORCE_DEFORMATION", ["sculpture", "archaeology"], "CHISEL_GOUGE",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 3, "PHYSICAL_BOUNCE", "CRACK", 1.05, 0.95, 2, 0.2, []),
    ("khoan", ["khoan thủng", "khoan sâu"], "FORCE_DEFORMATION", ["mechanics", "geology", "dentistry"], "DRILL_BORE",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 4, "LINEAR_STEP", "CRACK", 1.0, 1.0, 3, 0.3,
     [{"id": "debris_rings", "description": "debris concentric rings", "prompt": "drilling debris fragments", "scale": 0.22}]),
    ("xẻ đôi", ["chia đôi", "tách làm đôi"], "FORCE_DEFORMATION", ["general", "biology"], "BISECT_SPLIT",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 2, "PHYSICAL_BOUNCE", "SPLIT_HALF", 1.25, 0.75, 2, 0.2, []),
    ("tách rời", ["chia tách", "phân lập"], "FORCE_DEFORMATION", ["chemistry", "biology", "general"], "SEPARATE_ISOLATE",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 3, "LINEAR_STEP", "SPLIT_HALF", 1.2, 0.8, 3, 0.25, [])
]

# 4. Kéo, Giật, Xoắn (11 từ)
n1_keo = [
    ("kéo", ["lôi", "kéo lê"], "FORCE_DEFORMATION", ["physics", "general"], "PULL_TENSION",
     "DISCRETE_TRANSLATE", [-1.0, 0.0], 3, "LINEAR_STEP", "SQUASH_AND_STRETCH", 1.2, 0.85, 3, 0.2, []),
    ("giật", ["giật mạnh", "giật lùi"], "FORCE_DEFORMATION", ["general", "physics"], "JERK_TUG",
     "DISCRETE_TRANSLATE", [0.0, -1.0], 2, "PHYSICAL_BOUNCE", "SQUASH_AND_STRETCH", 0.9, 1.2, 2, 0.15, []),
    ("lôi", ["kéo đi", "lôi kéo"], "FORCE_DEFORMATION", ["general"], "DRAG_DISPLACE",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 2, 0.2, []),
    ("xoắn", ["vặn xoắn", "xoắn ốc"], "FORCE_DEFORMATION", ["mechanics", "biology"], "TORSION_TWIST",
     "SQUASH_AND_STRETCH", [0.0, 0.0], 4, "LINEAR_STEP", "SQUASH_AND_STRETCH", 0.8, 1.25, 3, 0.25, []),
    ("vặn", ["vặn chặt", "xoay vặn"], "FORCE_DEFORMATION", ["mechanics", "general"], "TORQUE_SCREW",
     "SQUASH_AND_STRETCH", [0.0, 0.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 2, 0.2, []),
    ("căng", ["kéo căng", "căng tròn"], "FORCE_DEFORMATION", ["physics", "general"], "TENSION_ELONGATE",
     "SQUASH_AND_STRETCH", [1.0, 0.0], 3, "LINEAR_STEP", "SQUASH_AND_STRETCH", 1.3, 0.8, 3, 0.2, []),
    ("kéo căng", ["căng ra", "giương"], "FORCE_DEFORMATION", ["physics", "mechanics"], "TENSILE_STRETCH",
     "SQUASH_AND_STRETCH", [1.0, 0.0], 4, "LINEAR_STEP", "SQUASH_AND_STRETCH", 1.35, 0.75, 3, 0.25, []),
    ("giằng", ["giằng co", "giật mạnh"], "FORCE_DEFORMATION", ["warfare", "general"], "WREST_YANK",
     "DISCRETE_TRANSLATE", [-1.0, 0.0], 2, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 2, 0.15, []),
    ("co kéo", ["kéo qua kéo lại"], "FORCE_DEFORMATION", ["general", "biology"], "TUG_OSCILLATE",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 4, "HOLD_JITTER", "NONE", 1.0, 1.0, 2, 0.2, []),
    ("nới", ["nới lỏng", "thả lỏng"], "FORCE_DEFORMATION", ["mechanics", "general"], "LOOSEN_EXPAND",
     "SQUASH_AND_STRETCH", [0.0, 0.0], 3, "LINEAR_STEP", "SQUASH_AND_STRETCH", 1.1, 1.1, 3, 0.2, []),
    ("bứt", ["ngắt đứt", "bứt phá"], "FORCE_DEFORMATION", ["botany", "general"], "SNAP_SEVER",
     "DISCRETE_TRANSLATE", [0.0, -1.0], 2, "PHYSICAL_BOUNCE", "SPLIT_HALF", 1.0, 1.0, 2, 0.15, [])
]

# 5. Đâm, Chọc, Xuyên (10 từ)
n1_dam = [
    ("đâm", ["chọc", "thọc"], "FORCE_DEFORMATION", ["warfare", "general"], "PIERCE_PUNCTURE",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 2, "PHYSICAL_BOUNCE", "CRACK", 1.05, 0.95, 2, 0.15, []),
    ("chọc", ["châm", "thọc"], "FORCE_DEFORMATION", ["general"], "POKE_PROD",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 2, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.1, []),
    ("xiên", ["xâu", "xiên qua"], "FORCE_DEFORMATION", ["culinary", "general"], "SKEWER_TRANSFIX",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 2, 0.2, []),
    ("chích", ["châm", "chích kim"], "FORCE_DEFORMATION", ["medicine", "biology"], "PRICK_INJECT",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 2, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 2, 0.15, []),
    ("tiêm", ["tiêm thuốc", "bơm tiêm"], "FORCE_DEFORMATION", ["medicine", "pharmacology"], "SYRINGE_INJECT",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 3, "LINEAR_STEP", "SQUASH_AND_STRETCH", 1.1, 1.1, 3, 0.25,
     [{"id": "liquid_infusion", "description": "medicine fluid droplet", "prompt": "translucent blue medicine droplet", "scale": 0.2}]),
    ("xuyên", ["xuyên qua", "luồn qua"], "FORCE_DEFORMATION", ["physics", "optics", "warfare"], "PENETRATE_THROUGH",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 3, "LINEAR_STEP", "CRACK", 1.0, 1.0, 2, 0.2, []),
    ("xuyên thủng", ["phá thủng", "đâm thủng"], "FORCE_DEFORMATION", ["mechanics", "naval"], "PERFORATE_BREACH",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 3, "PHYSICAL_BOUNCE", "CRACK", 1.1, 0.9, 3, 0.2, []),
    ("cắm", ["cắm sâu", "ghim vào"], "FORCE_DEFORMATION", ["botany", "construction", "history"], "IMPLANT_STAKE",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 2, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 2, 0.15, []),
    ("găm", ["bắn găm", "ghim chặt"], "FORCE_DEFORMATION", ["general", "warfare"], "LODGE_EMBED",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 2, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 2, 0.15, []),
    ("luồn", ["luồn lách", "xỏ qua"], "FORCE_DEFORMATION", ["medicine", "general"], "THREAD_SNAKE",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 2, 0.25, [])
]

# 6. Lực Sinh học & Tự nhiên (16 từ)
n1_sinh_hoc = [
    ("cắn", ["ngoạm", "cắn xé"], "FORCE_DEFORMATION", ["biology", "zoology"], "BITE_CLAMP",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 2, "PHYSICAL_BOUNCE", "CRACK", 1.15, 0.85, 2, 0.15, []),
    ("nhai", ["nghiền thức ăn"], "FORCE_DEFORMATION", ["biology"], "MASTICATE_CHEW",
     "SQUASH_AND_STRETCH", [0.0, 1.0], 4, "PHYSICAL_BOUNCE", "SQUASH_AND_STRETCH", 1.2, 0.8, 3, 0.2, []),
    ("gặm", ["gặm nhấm"], "FORCE_DEFORMATION", ["biology", "zoology"], "GNAW_NIBBLE",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 4, "HOLD_JITTER", "SHRINK_AND_DISAPPEAR", 0.9, 0.9, 3, 0.25, []),
    ("xé xác", ["phanh thây", "xé tan"], "FORCE_DEFORMATION", ["zoology", "nature"], "DISEMBOWEL_SHRED",
     "SQUASH_AND_STRETCH", [1.0, 0.0], 3, "PHYSICAL_BOUNCE", "FRAGMENT_BURST", 1.3, 0.7, 3, 0.2, []),
    ("bóp nghẹt", ["siết cổ", "nghẹt thở"], "FORCE_DEFORMATION", ["biology", "medicine"], "STRANGLE_CHOKE",
     "SQUASH_AND_STRETCH", [0.0, 0.0], 4, "LINEAR_STEP", "SQUASH_AND_STRETCH", 0.75, 1.25, 3, 0.25, []),
    ("co thắt", ["co rút", "thắt lại"], "FORCE_DEFORMATION", ["biology", "medicine"], "SPASM_CONTRACT",
     "SQUASH_AND_STRETCH", [0.0, 0.0], 3, "HOLD_JITTER", "SQUASH_AND_STRETCH", 0.8, 0.8, 2, 0.2, []),
    ("nghiền nát", ["tán vụn", "đè nát"], "FORCE_DEFORMATION", ["geology", "mechanics"], "PULVERIZE_CRUSH",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 3, "PHYSICAL_BOUNCE", "FRAGMENT_BURST", 1.4, 0.6, 3, 0.2,
     [{"id": "rock_shards", "description": "shattered stone fragments", "prompt": "shattered stone debris shards", "scale": 0.25}]),
    ("phá hủy", ["tàn phá", "hủy diệt"], "FORCE_DEFORMATION", ["warfare", "geology"], "DEMOLISH_DESTROY",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 3, "PHYSICAL_BOUNCE", "FRAGMENT_BURST", 1.3, 0.7, 3, 0.2, []),
    ("san phẳng", ["san bằng", "cày xới"], "FORCE_DEFORMATION", ["geography", "warfare"], "LEVEL_FLATTEN",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 4, "LINEAR_STEP", "SQUASH_AND_STRETCH", 1.5, 0.45, 4, 0.25, []),
    ("san bằng", ["san phẳng", "triệt hạ"], "FORCE_DEFORMATION", ["history", "warfare"], "RAZE_GROUND",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 3, "PHYSICAL_BOUNCE", "SQUASH_AND_STRETCH", 1.4, 0.5, 3, 0.2, []),
    ("nứt toác", ["rạn vỡ", "toác mỏ"], "FORCE_DEFORMATION", ["geology", "nature"], "FISSURE_RUPTURE",
     "SQUASH_AND_STRETCH", [1.0, 0.0], 3, "PHYSICAL_BOUNCE", "CRACK", 1.25, 0.85, 3, 0.2, []),
    ("nứt nẻ", ["khô nứt", "rạn nứt"], "FORCE_DEFORMATION", ["geography", "climate"], "DESICCATION_CRACK",
     "SQUASH_AND_STRETCH", [0.0, 0.0], 4, "LINEAR_STEP", "CRACK", 1.1, 0.95, 3, 0.25, []),
    ("vỡ vụn", ["tan nát", "vỡ tan"], "FORCE_DEFORMATION", ["physics", "ceramics"], "SHATTER_CRUMBLE",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 2, "PHYSICAL_BOUNCE", "FRAGMENT_BURST", 1.35, 0.65, 3, 0.15,
     [{"id": "ceramic_shards", "description": "broken porcelain pottery pieces", "prompt": "antique broken pottery shards", "scale": 0.26}]),
    ("vỡ tung", ["nổ vỡ", "bung vỡ"], "FORCE_DEFORMATION", ["physics", "chemistry"], "BURST_EXPLODE",
     "SQUASH_AND_STRETCH", [0.0, 0.0], 2, "PHYSICAL_BOUNCE", "FRAGMENT_BURST", 1.4, 0.6, 2, 0.15, []),
    ("sụt lún", ["lún xuống", "sụp đổ"], "FORCE_DEFORMATION", ["geology", "civil_engineering"], "SUBSIDENCE_SINK",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 4, "LINEAR_STEP", "SQUASH_AND_STRETCH", 1.15, 0.75, 3, 0.3, []),
    ("đè bẹp", ["nghiền bẹp", "đè nát"], "FORCE_DEFORMATION", ["geography", "physics", "mechanics"], "CRUSH_OVERWHELM",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 3, "PHYSICAL_BOUNCE", "SQUASH_AND_STRETCH", 1.45, 0.55, 3, 0.2, [])
]

# Nạp nhóm 1
for item in (n1_ep + n1_dap + n1_cat + n1_keo + n1_dam + n1_sinh_hoc):
    add_verb(*item)

# ==============================================================================
# NHÓM 2: SINH SẢN, XUẤT PHÁT & LAN TỎA (Emission & Propagation) — 80 ĐỘNG TỪ
# ==============================================================================

# 1. In ấn, Truyền thông & Sao chép (11 từ)
n2_in_an = [
    ("in ấn", ["ấn loát", "xuất bản"], "EMISSION_SPAWNING", ["media", "history", "craft"], "PRINT_PRESS",
     "SEQUENTIAL_SPAWN", [0.0, 1.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.2,
     [{"id": "printed_paper", "description": "freshly printed paper sheet", "prompt": "printed newspaper page cutout", "scale": 0.3}]),
    ("in", ["in ra", "in nổi"], "EMISSION_SPAWNING", ["media", "technology"], "DOCUMENT_PRINT",
     "SEQUENTIAL_SPAWN", [0.0, 1.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.2,
     [{"id": "photo_card", "description": "printed photobooth card", "prompt": "vintage monochrome photo card", "scale": 0.28}]),
    ("photocopy", ["sao chụp", "nhân bản tài liệu"], "EMISSION_SPAWNING", ["technology", "office"], "XEROX_REPLICATE",
     "SEQUENTIAL_SPAWN", [0.0, 1.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.25, []),
    ("dập nổi", ["khắc nổi", "ép nổi"], "EMISSION_SPAWNING", ["craft", "printing"], "EMBOSS_STAMP",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 2, "PHYSICAL_BOUNCE", "SQUASH_AND_STRETCH", 1.1, 0.9, 2, 0.15, []),
    ("khắc dấu", ["khắc triện", "đẽo dấu"], "EMISSION_SPAWNING", ["history", "craft"], "SEAL_CARVE",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 2, 0.2, []),
    ("đóng dấu", ["đóng triện", "chứng thực"], "EMISSION_SPAWNING", ["history", "bureaucracy"], "SEAL_IMPRINT",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 2, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 2, 0.15,
     [{"id": "red_wax_seal", "description": "vermilion red imperial wax stamp", "prompt": "antique red royal wax seal imprint", "scale": 0.25}]),
    ("xổ ảnh", ["in tráng ảnh", "rửa ảnh"], "EMISSION_SPAWNING", ["photography", "art"], "PHOTO_SLIDE_OUT",
     "SEQUENTIAL_SPAWN", [0.0, 1.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.3,
     [{"id": "photo_strip", "description": "vintage photo film strip", "prompt": "vintage monochrome photo film strip", "scale": 0.3}]),
    ("cuộn phim", ["quay phim", "lên phim"], "EMISSION_SPAWNING", ["cinema", "media"], "REEL_UNROLL",
     "SEQUENTIAL_SPAWN", [1.0, 0.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.25, []),
    ("xuất bản", ["phát hành", "ấn hành"], "EMISSION_SPAWNING", ["literature", "media"], "PUBLISH_RELEASE",
     "SEQUENTIAL_SPAWN", [0.0, 1.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.2, []),
    ("sao chép", ["chép lại", "nhân bản"], "EMISSION_SPAWNING", ["general", "computing"], "CLONE_DUPLICATE",
     "SEQUENTIAL_SPAWN", [1.0, 0.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.2, []),
    ("nhân bản", ["nhân giống", "sao chép vô tính"], "EMISSION_SPAWNING", ["biology", "genetics"], "CLONING_REPLICATE",
     "SEQUENTIAL_SPAWN", [1.0, 0.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.3, [])
]

# 2. Phát sóng, Bức xạ & Năng lượng (17 từ)
n2_phat_song = [
    ("phát sóng", ["truyền sóng", "phát thanh"], "EMISSION_SPAWNING", ["telecom", "physics"], "WAVE_BROADCAST",
     "SEQUENTIAL_SPAWN", [0.0, -1.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.2,
     [{"id": "radio_waves", "description": "concentric radio antenna wave rings", "prompt": "concentric radio broadcast wave rings", "scale": 0.32}]),
    ("truyền tin", ["gửi tín hiệu", "báo tin"], "EMISSION_SPAWNING", ["history", "military", "telecom"], "SIGNAL_RELAY",
     "SEQUENTIAL_SPAWN", [1.0, 0.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.2, []),
    ("phát thanh", ["truyền thanh", "loa truyền"], "EMISSION_SPAWNING", ["media", "audio"], "AUDIO_BROADCAST",
     "SEQUENTIAL_SPAWN", [1.0, 0.0], 3, "HOLD_JITTER", "NONE", 1.0, 1.0, 1, 0.2, []),
    ("phát tín hiệu", ["ra tín hiệu", "bắn pháo hiệu"], "EMISSION_SPAWNING", ["navigation", "naval", "telecom"], "BEACON_SIGNAL",
     "SEQUENTIAL_SPAWN", [0.0, -1.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.15,
     [{"id": "sonar_ping", "description": "underwater sonar acoustic wave pulse", "prompt": "green sonar ping circular radar pulse", "scale": 0.3}]),
    ("chiếu sáng", ["rọi sáng", "soi tỏ"], "EMISSION_SPAWNING", ["optics", "physics"], "BEAM_ILLUMINATE",
     "SCALE_REVEAL", [0.0, 1.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.2,
     [{"id": "light_cone", "description": "focused cone of bright optical light", "prompt": "translucent bright optical spotlight beam cone", "scale": 0.35}]),
    ("rọi", ["rọi đèn", "chiếu thẳng"], "EMISSION_SPAWNING", ["optics", "mining"], "SPOTLIGHT_FOCUS",
     "SCALE_REVEAL", [0.0, 1.0], 2, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.15, []),
    ("bật đèn", ["thắp sáng", "mở đèn"], "EMISSION_SPAWNING", ["general", "electricity"], "LAMP_IGNITE",
     "PULSE_EXPAND", [0.0, 0.0], 2, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.1, []),
    ("chớp sáng", ["nhấp nháy chớp", "sấm chớp"], "EMISSION_SPAWNING", ["weather", "optics"], "STROBE_FLASH",
     "PULSE_EXPAND", [0.0, 0.0], 2, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.05, []),
    ("nhấp nháy", ["chớp tắt", "lung linh"], "EMISSION_SPAWNING", ["optics", "astronomy"], "TWINKLE_BLINK",
     "HOLD_JITTER", [0.0, 0.0], 4, "HOLD_JITTER", "NONE", 1.0, 1.0, 1, 0.15, []),
    ("lóe sáng", ["bừng sáng", "bừng lên"], "EMISSION_SPAWNING", ["optics", "physics"], "GLINT_FLARE",
     "SCALE_REVEAL", [0.0, 0.0], 2, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.1, []),
    ("bức xạ", ["phát xạ", "tỏa tia"], "EMISSION_SPAWNING", ["physics", "nuclear"], "RADIATION_EMIT",
     "SEQUENTIAL_SPAWN", [0.0, 0.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.2,
     [{"id": "radiation_waves", "description": "invisible gamma rays ionizing lines", "prompt": "subtle yellow radiant energy burst rays", "scale": 0.3}]),
    ("phóng xạ", ["phát ra hạt phóng xạ"], "EMISSION_SPAWNING", ["nuclear_physics", "chemistry"], "RADIOACTIVE_DECAY",
     "SEQUENTIAL_SPAWN", [1.0, 0.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.2, []),
    ("tỏa nhiệt", ["phát nhiệt", "nung nóng"], "EMISSION_SPAWNING", ["thermodynamics", "physics"], "THERMAL_DISSIPATE",
     "PULSE_EXPAND", [0.0, -1.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.25, []),
    ("phát quang", ["lân tinh", "phát sáng sinh học"], "EMISSION_SPAWNING", ["marine_biology", "chemistry"], "BIOLUMINESCENCE",
     "PULSE_EXPAND", [0.0, 0.0], 3, "HOLD_JITTER", "NONE", 1.0, 1.0, 1, 0.2,
     [{"id": "bioluminescent_glow", "description": "deep sea cyan glowing halo", "prompt": "luminous cyan deep ocean organic glow halo", "scale": 0.35}]),
    ("phát tia", ["bắn tia", "phát tia laser"], "EMISSION_SPAWNING", ["optics", "physics"], "BEAM_RAY",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 2, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.1, []),
    ("phóng điện", ["phóng tia lửa", "đánh sét"], "EMISSION_SPAWNING", ["electricity", "physics"], "ELECTRIC_DISCHARGE",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 2, "PHYSICAL_BOUNCE", "CRACK", 1.05, 0.95, 2, 0.1,
     [{"id": "lightning_arc", "description": "blue high voltage electric spark arc", "prompt": "jagged blue electric lightning bolt arc", "scale": 0.28}]),
    ("truyền điện", ["dẫn điện", "tải điện"], "EMISSION_SPAWNING", ["electricity", "engineering"], "CURRENT_CONDUCTION",
     "SEQUENTIAL_SPAWN", [1.0, 0.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.2, [])
]

# 3. Phun, Bắn, Rải, Thổi (22 từ)
n2_phun_ban = [
    ("bắn", ["phóng đạn", "bắn tỉa"], "EMISSION_SPAWNING", ["warfare", "physics"], "PROJECTILE_FIRE",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 2, "PHYSICAL_BOUNCE", "SQUASH_AND_STRETCH", 0.9, 1.1, 2, 0.1, []),
    ("phóng", ["phóng tên lửa", "phóng tàu"], "EMISSION_SPAWNING", ["aerospace", "physics"], "ROCKET_LAUNCH",
     "DISCRETE_TRANSLATE", [0.0, -1.0], 4, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.3,
     [{"id": "exhaust_plume", "description": "rocket exhaust smoke flame plume", "prompt": "smoke plume rocket launch propellant", "scale": 0.35}]),
    ("xịt", ["xịt hơi", "xịt nước"], "EMISSION_SPAWNING", ["general", "chemistry"], "AEROSOL_SPRAY",
     "SEQUENTIAL_SPAWN", [1.0, 0.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.15, []),
    ("phun", ["phun trào", "xịt"], "EMISSION_SPAWNING", ["geology", "general"], "JET_ERUPT",
     "SEQUENTIAL_SPAWN", [0.0, -1.0], 3, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.2,
     [{"id": "magma_plume", "description": "volcanic lava smoke fountain", "prompt": "volcanic glowing lava smoke erupting fountain", "scale": 0.35}]),
    ("phun sương", ["tạo sương", "sương mù"], "EMISSION_SPAWNING", ["botany", "technology"], "MIST_DISPERSE",
     "SEQUENTIAL_SPAWN", [0.0, 1.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.25, []),
    ("phun trào", ["bùng phát nham thạch"], "EMISSION_SPAWNING", ["geology", "volcanology"], "VOLCANO_ERUPTION",
     "SEQUENTIAL_SPAWN", [0.0, -1.0], 4, "PHYSICAL_BOUNCE", "FRAGMENT_BURST", 1.3, 0.7, 3, 0.25, []),
    ("tuôn", ["tuôn ra", "chảy xiết"], "EMISSION_SPAWNING", ["hydrology", "nature"], "GUSH_TORRENT",
     "SEQUENTIAL_SPAWN", [0.0, 1.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.2, []),
    ("trào", ["dâng trào", "trào bọt"], "EMISSION_SPAWNING", ["chemistry", "hydrology"], "SURGE_OVERFLOW",
     "PULSE_EXPAND", [0.0, -1.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.2, []),
    ("tràn", ["tràn bờ", "tràn lan"], "EMISSION_SPAWNING", ["geography", "hydrology"], "SPILL_FLOOD",
     "SEQUENTIAL_SPAWN", [1.0, 0.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.25, []),
    ("bùng phát", ["bùng nổ", "bùng cháy"], "EMISSION_SPAWNING", ["epidemiology", "chemistry", "warfare"], "OUTBREAK_ERUPT",
     "PULSE_EXPAND", [0.0, 0.0], 3, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.15, []),
    ("nổ tung", ["bộc phá", "vỡ òa"], "EMISSION_SPAWNING", ["physics", "military"], "BLAST_DETONATE",
     "PULSE_EXPAND", [0.0, 0.0], 2, "PHYSICAL_BOUNCE", "FRAGMENT_BURST", 1.5, 0.5, 3, 0.1,
     [{"id": "blast_smoke", "description": "explosive blast smoke cloud", "prompt": "billowing orange explosion blast fireball smoke", "scale": 0.38}]),
    ("nổ", ["phát nổ", "bùng nổ"], "EMISSION_SPAWNING", ["physics", "chemistry"], "DETONATE_BANG",
     "PULSE_EXPAND", [0.0, 0.0], 2, "PHYSICAL_BOUNCE", "FRAGMENT_BURST", 1.3, 0.7, 2, 0.1, []),
    ("thổi", ["thổi bay", "thổi luồng"], "EMISSION_SPAWNING", ["meteorology", "general"], "GUST_BLOW",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 3, "LINEAR_STEP", "DISPLACE_DRIFT", 1.0, 1.0, 2, 0.2, []),
    ("phả", ["phả khói", "thổi hơi"], "EMISSION_SPAWNING", ["general", "industry"], "EXHALE_PUFF",
     "SEQUENTIAL_SPAWN", [0.0, -1.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.2, []),
    ("rắc", ["rắc muối", "rắc phấn"], "EMISSION_SPAWNING", ["culinary", "general"], "SPRINKLE_SCATTER",
     "SEQUENTIAL_SPAWN", [0.0, 1.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.2, []),
    ("rải", ["rải truyền đơn", "rải sỏi"], "EMISSION_SPAWNING", ["history", "military", "construction"], "STREW_SPREAD",
     "SEQUENTIAL_SPAWN", [1.0, 1.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.25, []),
    ("vương vãi", ["rơi vãi", "vung vãi"], "EMISSION_SPAWNING", ["general"], "SCATTER_DROP",
     "SEQUENTIAL_SPAWN", [0.0, 1.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.2, []),
    ("gieo", ["gieo hạt", "gieo mầm"], "EMISSION_SPAWNING", ["agriculture", "botany"], "SOW_SEED",
     "SEQUENTIAL_SPAWN", [0.0, 1.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.2,
     [{"id": "seedlings", "description": "tiny agricultural crop seeds falling", "prompt": "golden wheat seeds falling cutout", "scale": 0.2}]),
    ("gieo rắc", ["gieo rắc mầm mống"], "EMISSION_SPAWNING", ["history", "epidemiology"], "SOW_DISCORD",
     "SEQUENTIAL_SPAWN", [1.0, 1.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.2, []),
    ("phát tán", ["tán phát", "lan rộng"], "EMISSION_SPAWNING", ["botany", "epidemiology"], "DISPERSE_PROPAGATE",
     "SEQUENTIAL_SPAWN", [1.0, 1.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.25, []),
    ("lan tỏa", ["lan truyền", "tỏa rộng"], "EMISSION_SPAWNING", ["general", "physics"], "DIFFUSE_RADIATE",
     "PULSE_EXPAND", [0.0, 0.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.3, []),
    ("khuếch tán", ["hòa tan", "khuếch tán phân tử"], "EMISSION_SPAWNING", ["chemistry", "physics"], "MOLECULAR_DIFFUSION",
     "SEQUENTIAL_SPAWN", [1.0, 1.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.3, [])
]

# 4. Sinh học & Vi sinh (23 từ)
n2_sinh_hoc = [
    ("sinh sản", ["sinh sôi", "sinh đẻ"], "EMISSION_SPAWNING", ["biology", "zoology"], "REPRODUCE_BREED",
     "SEQUENTIAL_SPAWN", [1.0, 0.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.3, []),
    ("đẻ", ["sinh con", "đẻ trứng"], "EMISSION_SPAWNING", ["zoology", "biology"], "LAY_EGG_CALVE",
     "SEQUENTIAL_SPAWN", [0.0, 1.0], 3, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.25,
     [{"id": "spotted_egg", "description": "oval bird reptile egg", "prompt": "antique natural history spotted specimen egg", "scale": 0.22}]),
    ("nở", ["nở hoa", "nở trứng"], "EMISSION_SPAWNING", ["botany", "zoology"], "BLOOM_HATCH",
     "SCALE_REVEAL", [0.0, 0.0], 3, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.2,
     [{"id": "blooming_petals", "description": "unfolding floral petals", "prompt": "botanical illustration blooming petals unfolding", "scale": 0.3}]),
    ("ấp", ["ấp trứng", "ủ ấm"], "EMISSION_SPAWNING", ["zoology"], "INCUBATE_BROOD",
     "HOLD_JITTER", [0.0, 0.0], 3, "HOLD_JITTER", "NONE", 1.0, 1.0, 1, 0.2, []),
    ("nảy mầm", ["mọc mầm", "bén rễ"], "EMISSION_SPAWNING", ["botany", "agriculture"], "GERMINATE_SPROUT",
     "SCALE_REVEAL", [0.0, -1.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.3,
     [{"id": "green_sprout", "description": "fresh green plant sprout shoot", "prompt": "botanical green botanical seedling sprout", "scale": 0.25}]),
    ("đâm chồi", ["nảy chồi", "ra lộc"], "EMISSION_SPAWNING", ["botany"], "SHOOT_BUD",
     "SCALE_REVEAL", [0.0, -1.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.25, []),
    ("nảy chồi", ["đâm chồi nảy lộc"], "EMISSION_SPAWNING", ["botany"], "BUD_BURGEON",
     "SCALE_REVEAL", [1.0, -1.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.25, []),
    ("phân bào", ["phân chia tế bào", "nguyên phân"], "EMISSION_SPAWNING", ["cell_biology", "genetics"], "MITOSIS_DIVISION",
     "SQUASH_AND_STRETCH", [1.0, 0.0], 4, "PHYSICAL_BOUNCE", "SPLIT_HALF", 1.25, 0.75, 3, 0.25,
     [{"id": "daughter_cell", "description": "twin daughter biological cells", "prompt": "microscopic dividing twin biological cells", "scale": 0.32}]),
    ("nhân đôi", ["tự nhân đôi", "nhân bản"], "EMISSION_SPAWNING", ["genetics", "biology"], "DNA_REPLICATION",
     "SEQUENTIAL_SPAWN", [1.0, 0.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.25, []),
    ("sinh sôi", ["nảy nở", "sinh sôi nảy nở"], "EMISSION_SPAWNING", ["biology", "ecology"], "MULTIPLY_PROLIFERATE",
     "SEQUENTIAL_SPAWN", [1.0, 1.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.3, []),
    ("thụ phấn", ["tiếp phấn", "giao phấn"], "EMISSION_SPAWNING", ["botany", "entomology"], "POLLINATE",
     "SEQUENTIAL_SPAWN", [0.0, 1.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.2,
     [{"id": "pollen_grains", "description": "golden pollen microscopic grains", "prompt": "microscopic golden pollen grain dust", "scale": 0.22}]),
    ("thụ tinh", ["kết hợp giao tử"], "EMISSION_SPAWNING", ["biology", "embryology"], "FERTILIZATION",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 3, "PHYSICAL_BOUNCE", "PULSE_EXPAND", 1.2, 1.2, 2, 0.25, []),
    ("phóng noãn", ["rụng trứng"], "EMISSION_SPAWNING", ["endocrinology", "zoology"], "OVULATION",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 3, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.2, []),
    ("tiết dịch", ["tiết chất nhờn", "ứa dịch"], "EMISSION_SPAWNING", ["physiology", "zoology"], "SECRETE_FLUID",
     "SEQUENTIAL_SPAWN", [0.0, 1.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.2,
     [{"id": "viscous_mucus", "description": "glistening viscous slime droplet", "prompt": "viscous glistening translucent secretion drop", "scale": 0.22}]),
    ("tiết men", ["tiết enzyme"], "EMISSION_SPAWNING", ["biochemistry", "digestive"], "ENZYME_EXUDE",
     "SEQUENTIAL_SPAWN", [0.0, 1.0], 3, "LINEAR_STEP", "SQUASH_AND_STRETCH", 0.9, 0.9, 2, 0.25, []),
    ("bài tiết", ["thải trừ", "tiêu thoát"], "EMISSION_SPAWNING", ["physiology", "medicine"], "EXCRETE_ELIMINATE",
     "SEQUENTIAL_SPAWN", [0.0, 1.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.2, []),
    ("rỉ", ["rỉ nước", "thấm rỉ"], "EMISSION_SPAWNING", ["hydrology", "pathology"], "OOZE_SEEP",
     "SEQUENTIAL_SPAWN", [0.0, 1.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.3, []),
    ("ứa", ["ứa nước mắt", "ứa máu"], "EMISSION_SPAWNING", ["physiology", "medicine"], "WELT_EXUDE",
     "PULSE_EXPAND", [0.0, 1.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.2, []),
    ("toát mồ hôi", ["đổ mồ hôi", "tiết mồ hôi"], "EMISSION_SPAWNING", ["physiology"], "PERSPIRATION",
     "SEQUENTIAL_SPAWN", [0.0, 1.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.2, []),
    ("lây lan", ["truyền nhiễm", "lan truyền dịch"], "EMISSION_SPAWNING", ["epidemiology", "virology"], "TRANSMIT_CONTAGION",
     "SEQUENTIAL_SPAWN", [1.0, 1.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.3, []),
    ("lây nhiễm", ["nhiễm chéo", "truyền bệnh"], "EMISSION_SPAWNING", ["medicine", "virology"], "INFECT_CONTAMINATE",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 3, "LINEAR_STEP", "PULSE_EXPAND", 1.15, 1.15, 2, 0.2, []),
    ("nhiễm khuẩn", ["nhiễm trùng", "viêm nhiễm"], "EMISSION_SPAWNING", ["medicine", "microbiology"], "BACTERIAL_SEPSIS",
     "PULSE_EXPAND", [0.0, 0.0], 3, "HOLD_JITTER", "SQUASH_AND_STRETCH", 0.9, 0.9, 3, 0.25, []),
    ("phát tán bào tử", ["gieo rắc nấm", "bung bào tử"], "EMISSION_SPAWNING", ["mycology", "botany"], "SPORE_BURST",
     "SEQUENTIAL_SPAWN", [1.0, -1.0], 4, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.25,
     [{"id": "fungal_spores", "description": "cloud of microscopic fungal spores", "prompt": "cloud of microscopic fungal dust spores", "scale": 0.28}]),
]

# 5. Lịch sử & Hiệu lệnh (7 từ)
n2_hieu_lenh = [
    ("ban chiếu", ["hạ chiếu", "ban sắc phong"], "EMISSION_SPAWNING", ["history", "imperial"], "IMPERIAL_EDICT",
     "SEQUENTIAL_SPAWN", [0.0, 1.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.3,
     [{"id": "imperial_decree", "description": "unrolled silk imperial decree scroll", "prompt": "antique imperial Chinese silk decree scroll with dragon seal", "scale": 0.32}]),
    ("truyền hịch", ["phát hịch", "hịch tướng sĩ"], "EMISSION_SPAWNING", ["history", "military"], "CALL_TO_ARMS",
     "SEQUENTIAL_SPAWN", [0.0, 1.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.25, []),
    ("phát lệnh", ["truyền lệnh", "ban lệnh"], "EMISSION_SPAWNING", ["military", "command"], "ORDER_ISSUE",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 2, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.15,
     [{"id": "tally_tablet", "description": "military bronze tiger tally credential", "prompt": "ancient Chinese bronze tiger tally credential", "scale": 0.25}]),
    ("hạ lệnh", ["ra chỉ dụ", "chỉ huy"], "EMISSION_SPAWNING", ["military", "naval"], "DECREE_COMMAND",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 2, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.15, []),
    ("ban hành", ["công bố", "ban bố luật"], "EMISSION_SPAWNING", ["history", "jurisprudence"], "PROMULGATE_LAW",
     "SEQUENTIAL_SPAWN", [0.0, 1.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.25, []),
    ("dấy binh", ["khởi binh", "hưng binh"], "EMISSION_SPAWNING", ["history", "warfare"], "MOBILIZE_TROOPS",
     "SEQUENTIAL_SPAWN", [1.0, 0.0], 4, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.3,
     [{"id": "battle_standard", "description": "embroidered ancient silk war battle banner", "prompt": "ancient silk triangular battle banner on spear", "scale": 0.3}]),
    ("chiêu mộ", ["tuyển mộ", "chiêu binh"], "EMISSION_SPAWNING", ["history", "sociology"], "RECRUIT_CONSCRIPT",
     "SEQUENTIAL_SPAWN", [1.0, 0.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.25, [])
]

# Nạp nhóm 2
for item in (n2_in_an + n2_phat_song + n2_phun_ban + n2_sinh_hoc + n2_hieu_lenh):
    add_verb(*item)

# ==============================================================================
# NHÓM 3: DI CHUYỂN, DẪN ĐƯỜNG & HÀNH TRÌNH (Locomotion & Navigation) — 75 ĐỘNG TỪ
# ==============================================================================

# 1. Chuyển động Cơ thể & Phương tiện (23 từ)
n3_phuong_tien = [
    ("chạy", ["chạy nhanh", "phi nước đại"], "LOCOMOTION_NAVIGATION", ["general", "zoology"], "RUN_SPRINT",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.2, []),
    ("đi", ["bước đi", "tiến bước"], "LOCOMOTION_NAVIGATION", ["general"], "WALK_STRIDE",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.25, []),
    ("bước", ["bước chân", "dạo bước"], "LOCOMOTION_NAVIGATION", ["general"], "STEP_PACE",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.2, []),
    ("rảo bước", ["bước mau", "rảo nhanh"], "LOCOMOTION_NAVIGATION", ["general"], "QUICKEN_PACE",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.2, []),
    ("bò", ["bò lê", "bò sát"], "LOCOMOTION_NAVIGATION", ["zoology", "biology"], "CRAWL_CREEP",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 5, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.3, []),
    ("trườn", ["trườn mình", "uốn éo"], "LOCOMOTION_NAVIGATION", ["zoology", "herpetology"], "SLITHER_GLIDE",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.25, []),
    ("nhảy", ["nhảy vọt", "nhảy bật"], "LOCOMOTION_NAVIGATION", ["zoology", "physics"], "JUMP_LEAP",
     "DISCRETE_TRANSLATE", [1.0, -1.0], 3, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.2, []),
    ("bật", ["bật nảy", "bật lên"], "LOCOMOTION_NAVIGATION", ["physics", "sports"], "BOUND_RICOCHET",
     "DISCRETE_TRANSLATE", [0.0, -1.0], 2, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.15, []),
    ("phóng nhanh", ["lao vun vút", "tăng tốc"], "LOCOMOTION_NAVIGATION", ["transport", "mechanics"], "DASH_HURTLE",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 3, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.15, []),
    ("phi", ["phi ngựa", "lao đi"], "LOCOMOTION_NAVIGATION", ["history", "transport"], "GALLOP_CHARGE",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 3, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.15, []),
    ("lướt", ["lướt sóng", "lướt nhẹ"], "LOCOMOTION_NAVIGATION", ["marine", "aviation"], "GLIDE_SKIM",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.25, []),
    ("trượt", ["trượt băng", "trượt dốc"], "LOCOMOTION_NAVIGATION", ["physics", "sports"], "SLIDE_SKID",
     "DISCRETE_TRANSLATE", [1.0, 1.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.2, []),
    ("lăn", ["lăn tròn", "lăn bánh"], "LOCOMOTION_NAVIGATION", ["mechanics", "general"], "ROLL_TUMBLE",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.25, []),
    ("rơi", ["rơi xuống", "chao đảo rơi"], "LOCOMOTION_NAVIGATION", ["physics", "gravitation"], "DROP_FALL",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 3, "PHYSICAL_BOUNCE", "SQUASH_AND_STRETCH", 1.15, 0.85, 2, 0.2, []),
    ("rơi tự do", ["lao dốc tự do"], "LOCOMOTION_NAVIGATION", ["physics", "aerospace"], "FREE_FALL",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 4, "PHYSICAL_BOUNCE", "SQUASH_AND_STRETCH", 1.2, 0.8, 2, 0.25, []),
    ("rụng", ["rụng lá", "rụng quả"], "LOCOMOTION_NAVIGATION", ["botany"], "DETACH_DROP",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.2, []),
    ("đáp", ["hạ cánh nhẹ nhàng", "đậu"], "LOCOMOTION_NAVIGATION", ["aviation", "ornithology"], "TOUCHDOWN_PERCH",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 3, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.2, []),
    ("hạ cánh", ["tiếp đất"], "LOCOMOTION_NAVIGATION", ["aviation", "aerospace"], "AIRCRAFT_LANDING",
     "DISCRETE_TRANSLATE", [1.0, 1.0], 4, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.25, []),
    ("cất cánh", ["rời phi đạo", "vút lên"], "LOCOMOTION_NAVIGATION", ["aviation", "aerospace"], "TAKEOFF_ASCENT",
     "DISCRETE_TRANSLATE", [1.0, -1.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.25, []),
    ("bay", ["bay lượn", "bay bổng"], "LOCOMOTION_NAVIGATION", ["aviation", "ornithology"], "FLY_SOAR",
     "DISCRETE_TRANSLATE", [1.0, -0.5], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.25, []),
    ("lượn", ["chao lượn", "lượn vòng"], "LOCOMOTION_NAVIGATION", ["aviation", "nature"], "CIRCLING_BANK",
     "DISCRETE_TRANSLATE", [1.0, 0.5], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.25, []),
    ("liệng", ["chao liệng", "nghiêng cánh"], "LOCOMOTION_NAVIGATION", ["ornithology"], "SWOOP_DIVE",
     "DISCRETE_TRANSLATE", [1.0, 1.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.2, []),
    ("lơ lửng", ["treo lơ lửng", "trôi bồng bềnh"], "LOCOMOTION_NAVIGATION", ["physics", "aerospace"], "HOVER_LEVITATE",
     "HOLD_JITTER", [0.0, 0.0], 4, "HOLD_JITTER", "NONE", 1.0, 1.0, 1, 0.3, [])
]

# 2. Đại dương & Thủy văn (20 từ)
n3_dai_duong = [
    ("bơi", ["bơi lội", "vẫy vùng"], "LOCOMOTION_NAVIGATION", ["marine_biology", "sports"], "SWIM_PROPEL",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.25, []),
    ("lặn", ["ngụp lặn", "chìm sâu"], "LOCOMOTION_NAVIGATION", ["oceanography", "marine"], "DIVE_SUBMERGE",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.25,
     [{"id": "air_bubbles", "description": "rising aquatic aeration bubbles", "prompt": "translucent aquatic water air bubbles rising", "scale": 0.25}]),
    ("lặn sâu", ["thám hiểm vực thẳm"], "LOCOMOTION_NAVIGATION", ["oceanography", "deep_sea"], "DEEP_BATHYSCAPHE",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.3, []),
    ("chìm", ["đắm", "chìm nghỉm"], "LOCOMOTION_NAVIGATION", ["naval", "physics"], "SINK_FOUNDER",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.3, []),
    ("nổi", ["nổi lên", "nổi bồng bềnh"], "LOCOMOTION_NAVIGATION", ["physics", "hydrology"], "FLOAT_SURFACE",
     "DISCRETE_TRANSLATE", [0.0, -1.0], 3, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.2, []),
    ("trôi", ["trôi theo dòng", "trôi nổi"], "LOCOMOTION_NAVIGATION", ["hydrology", "nature"], "DRIFT_FLOW",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.3, []),
    ("dạt", ["dạt vào bờ", "dạt trôi"], "LOCOMOTION_NAVIGATION", ["marine", "geography"], "WASH_ASHORE",
     "DISCRETE_TRANSLATE", [1.0, 0.5], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.25, []),
    ("trôi dạt", ["lưu lạc", "bập bềnh"], "LOCOMOTION_NAVIGATION", ["oceanography"], "CASTAWAY_DRIFT",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.3, []),
    ("chảy", ["chảy róc rách", "tuôn chảy"], "LOCOMOTION_NAVIGATION", ["hydrology"], "STREAM_FLOW",
     "DISCRETE_TRANSLATE", [1.0, 0.5], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.25, []),
    ("tuôn chảy", ["cuồn cuộn chảy"], "LOCOMOTION_NAVIGATION", ["hydrology", "geography"], "CATARACT_RUSH",
     "DISCRETE_TRANSLATE", [1.0, 1.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.25, []),
    ("cuộn", ["cuộn sóng", "cuộn tròn"], "LOCOMOTION_NAVIGATION", ["oceanography", "meteorology"], "BILLOW_CURL",
     "SQUASH_AND_STRETCH", [1.0, 0.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.25, []),
    ("xoáy", ["xoáy nước", "cuộn xoáy"], "LOCOMOTION_NAVIGATION", ["oceanography", "hydrology"], "MAELSTROM_VORTEX",
     "SQUASH_AND_STRETCH", [0.0, 0.0], 4, "PHYSICAL_BOUNCE", "SHRINK_AND_DISAPPEAR", 0.7, 0.7, 3, 0.25,
     [{"id": "water_vortex", "description": "swirling whirlpool water current", "prompt": "circular ocean whirlpool vortex current", "scale": 0.35}]),
    ("trào dâng", ["dâng cao", "triều cường"], "LOCOMOTION_NAVIGATION", ["oceanography", "meteorology"], "TIDAL_SURGE",
     "DISCRETE_TRANSLATE", [0.0, -1.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.25, []),
    ("rút cạn", ["thủy triều rút", "cạn khô"], "LOCOMOTION_NAVIGATION", ["oceanography"], "EBB_RECEDE",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.3, []),
    ("sóng xô", ["vỗ bờ", "sóng dập"], "LOCOMOTION_NAVIGATION", ["marine"], "WAVE_BUFFET",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 3, "PHYSICAL_BOUNCE", "SQUASH_AND_STRETCH", 1.1, 0.9, 2, 0.2, []),
    ("dập dềnh", ["nhấp nhô", "bồng bềnh"], "LOCOMOTION_NAVIGATION", ["marine"], "BOB_UNDULATE",
     "HOLD_JITTER", [0.0, 1.0], 4, "HOLD_JITTER", "NONE", 1.0, 1.0, 1, 0.25, []),
    ("ngập", ["ngập úng", "nhấn chìm"], "LOCOMOTION_NAVIGATION", ["hydrology", "geography"], "INUNDATE_SUBMERGE",
     "DISCRETE_TRANSLATE", [0.0, -1.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.3, []),
    ("chèo", ["chèo thuyền", "khua mái chèo"], "LOCOMOTION_NAVIGATION", ["nautical", "sports"], "ROW_OAR",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.25, []),
    ("lái thuyền", ["cầm lái", "điều hướng"], "LOCOMOTION_NAVIGATION", ["nautical", "navigation"], "STEER_HELM",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.2, []),
    ("dong buồm", ["giương buồm", "căng buồm ra khơi"], "LOCOMOTION_NAVIGATION", ["history", "nautical"], "HOIST_SAILS",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.3,
     [{"id": "vintage_compass", "description": "vintage brass marine navigational compass", "prompt": "antique brass maritime ship compass rose", "scale": 0.28}]),
]

# 3. Địa chất, Khí quyển & Vũ trụ (12 từ)
n3_dia_chat = [
    ("xói mòn", ["bào mòn", "rửa trôi"], "LOCOMOTION_NAVIGATION", ["geology", "geomorphology"], "EROSION_WEAR",
     "DISCRETE_TRANSLATE", [1.0, 1.0], 4, "LINEAR_STEP", "SQUASH_AND_STRETCH", 0.9, 0.9, 3, 0.3, []),
    ("sạt lở", ["lở đất", "sụp đổ sườn"], "LOCOMOTION_NAVIGATION", ["geology", "natural_disaster"], "LANDSLIDE_SLUMP",
     "DISCRETE_TRANSLATE", [1.0, 1.0], 3, "PHYSICAL_BOUNCE", "FRAGMENT_BURST", 1.2, 0.8, 3, 0.2, []),
    ("trồi lên", ["nhô lên", "nâng cao"], "LOCOMOTION_NAVIGATION", ["tectonics", "geology"], "TECTONIC_UPLIFT",
     "DISCRETE_TRANSLATE", [0.0, -1.0], 4, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.25, []),
    ("dịch chuyển lục địa", ["trôi dạt lục địa"], "LOCOMOTION_NAVIGATION", ["tectonics", "geology"], "CONTINENTAL_DRIFT",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 5, "LINEAR_STEP", "CRACK", 1.1, 0.95, 3, 0.35, []),
    ("gió thổi", ["gió lùa", "thổi vi vút"], "LOCOMOTION_NAVIGATION", ["meteorology"], "WIND_BREEZE",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.25, []),
    ("lốc xoáy", ["vòi rồng", "bão xoáy"], "LOCOMOTION_NAVIGATION", ["meteorology", "extreme_weather"], "TORNADO_CYCLONE",
     "SQUASH_AND_STRETCH", [0.0, 0.0], 4, "PHYSICAL_BOUNCE", "SHRINK_AND_DISAPPEAR", 0.8, 1.2, 3, 0.25,
     [{"id": "cyclone_funnel", "description": "swirling funnel cloud tornado", "prompt": "antique etching tornado vortex cloud", "scale": 0.35}]),
    ("quay quanh", ["chuyển động quay", "lượn quanh"], "LOCOMOTION_NAVIGATION", ["astronomy", "orbital_mechanics"], "ORBIT_REVOLVE",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.3, []),
    ("tự quay", ["tự xoay quanh trục"], "LOCOMOTION_NAVIGATION", ["astronomy", "geophysics"], "PLANETARY_ROTATION",
     "SQUASH_AND_STRETCH", [0.0, 0.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.25, []),
    ("chuyển động quỹ đạo", ["bay theo quỹ đạo"], "LOCOMOTION_NAVIGATION", ["astronomy", "aerospace"], "KEPLERIAN_ORBIT",
     "DISCRETE_TRANSLATE", [1.0, 0.5], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.3, []),
    ("hút vào", ["hút lại", "trọng lực kéo"], "LOCOMOTION_NAVIGATION", ["astrophysics", "black_hole"], "GRAVITATIONAL_ATTRACT",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 4, "PHYSICAL_BOUNCE", "SQUASH_AND_STRETCH", 0.7, 1.3, 3, 0.25,
     [{"id": "event_horizon", "description": "gravitational lensing accretion disk", "prompt": "black hole glowing accretion disk ring", "scale": 0.35}]),
    ("đẩy ra", ["đẩy lùi", "lực đẩy"], "LOCOMOTION_NAVIGATION", ["physics", "magnetism"], "MAGNETIC_REPEL",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 3, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.2, []),
    ("va chạm thiên thạch", ["thiên thạch đâm"], "LOCOMOTION_NAVIGATION", ["astronomy", "planetary"], "METEOR_IMPACT",
     "DISCRETE_TRANSLATE", [1.0, 1.0], 3, "PHYSICAL_BOUNCE", "FRAGMENT_BURST", 1.4, 0.6, 3, 0.15,
     [{"id": "impact_crater", "description": "ejecta rim impact crater", "prompt": "meteor impact dust crater blast rim", "scale": 0.38}])
]

# 4. Sinh học & Xâm nhập (10 từ)
n3_xam_nhap = [
    ("di cư", ["di chuyển đàn", "trú đông"], "LOCOMOTION_NAVIGATION", ["zoology", "ecology"], "HERD_MIGRATION",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.3, []),
    ("săn mồi", ["lùng mồi", "truy đuổi"], "LOCOMOTION_NAVIGATION", ["zoology", "wildlife"], "PREDATORY_STALK",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.25, []),
    ("rình rập", ["núp lùm", "chờ thời cơ"], "LOCOMOTION_NAVIGATION", ["zoology", "military"], "AMBUSH_LURK",
     "HOLD_JITTER", [0.0, 0.0], 4, "HOLD_JITTER", "NONE", 1.0, 1.0, 1, 0.25, []),
    ("rượt đuổi", ["đuổi bắt", "truy kích"], "LOCOMOTION_NAVIGATION", ["zoology", "military"], "CHASE_PURSUIT",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 4, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.2, []),
    ("luồn lách", ["len lỏi", "lách qua"], "LOCOMOTION_NAVIGATION", ["general", "biology"], "WEAVE_DODGE",
     "DISCRETE_TRANSLATE", [1.0, 0.5], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.25, []),
    ("len lỏi", ["thâm nhập kẽ hở"], "LOCOMOTION_NAVIGATION", ["biology", "botany"], "INFILTRATE_CREEP",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.25, []),
    ("thâm nhập", ["xâm nhập", "đột nhập"], "LOCOMOTION_NAVIGATION", ["virology", "military"], "PENETRATE_BREACH",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 3, "PHYSICAL_BOUNCE", "CRACK", 1.05, 0.95, 2, 0.2, []),
    ("xâm lấn", ["bành trướng", "xâm chiếm"], "LOCOMOTION_NAVIGATION", ["oncology", "geopolitics"], "INVASIVE_ENCROACH",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 4, "LINEAR_STEP", "SQUASH_AND_STRETCH", 0.9, 0.9, 3, 0.3, []),
    ("lưu thông máu", ["tuần hoàn máu", "chảy trong mạch"], "LOCOMOTION_NAVIGATION", ["cardiology", "anatomy"], "BLOOD_CIRCULATION",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.25,
     [{"id": "erythrocyte", "description": "red blood cell disc", "prompt": "biconcave red blood cell erythrocyte cutout", "scale": 0.22}]),
    ("vận chuyển oxy", ["tải oxy"], "LOCOMOTION_NAVIGATION", ["biochemistry", "hematology"], "OXYGEN_TRANSPORT",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.2, [])
]

# 5. Lịch sử & Thám hiểm (10 từ)
n3_tham_hiem = [
    ("hành quân", ["tiến quân", "hành binh"], "LOCOMOTION_NAVIGATION", ["history", "military"], "TROOP_MARCH",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.3, []),
    ("tiến công", ["tấn công", "xông lên"], "LOCOMOTION_NAVIGATION", ["warfare", "history"], "ASSAULT_ADVANCE",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 3, "PHYSICAL_BOUNCE", "SQUASH_AND_STRETCH", 0.9, 1.1, 2, 0.15, []),
    ("rút lui", ["thoái lui", "bảo toàn lực lượng"], "LOCOMOTION_NAVIGATION", ["warfare", "tactics"], "TACTICAL_RETREAT",
     "DISCRETE_TRANSLATE", [-1.0, 0.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.2, []),
    ("viễn chinh", ["chinh phạt", "đoàn viễn chinh"], "LOCOMOTION_NAVIGATION", ["history", "geography"], "EXPEDITION_VOYAGE",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 5, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.35, []),
    ("thám hiểm", ["khám phá", "thám trắc"], "LOCOMOTION_NAVIGATION", ["geography", "history", "deep_sea"], "EXPLORE_SCOUT",
     "DISCRETE_TRANSLATE", [1.0, 0.5], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.25,
     [{"id": "vintage_lantern", "description": "antique brass exploration oil lantern", "prompt": "antique brass exploration hurricane oil lamp", "scale": 0.26}]),
    ("tuần tra", ["tuần tiễu", "canh gác"], "LOCOMOTION_NAVIGATION", ["military", "security"], "PATROL_RECON",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.25, []),
    ("vượt biên", ["băng qua biên giới"], "LOCOMOTION_NAVIGATION", ["geopolitics", "history"], "BORDER_CROSSING",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.25, []),
    ("vượt biển", ["băng qua đại dương", "vượt sóng"], "LOCOMOTION_NAVIGATION", ["maritime", "history"], "OCEAN_TRANSIT",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.3, []),
    ("đổ bộ", ["đáp lên bờ", "tiến quân lên bờ"], "LOCOMOTION_NAVIGATION", ["naval_warfare", "history"], "AMPHIBIOUS_LANDING",
     "DISCRETE_TRANSLATE", [1.0, 0.5], 4, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.25, []),
    ("chiếm lĩnh", ["làm chủ", "chiếm đóng"], "LOCOMOTION_NAVIGATION", ["warfare", "history"], "OCCUPY_CAPTURE",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 3, "PHYSICAL_BOUNCE", "SQUASH_AND_STRETCH", 1.1, 0.9, 2, 0.2, [])
]

# Nạp nhóm 3
for item in (n3_phuong_tien + n3_dai_duong + n3_dia_chat + n3_xam_nhap + n3_tham_hiem):
    add_verb(*item)

# ==============================================================================
# NHÓM 4: QUAN SÁT, BIẾN ĐỔI & TƯƠNG TÁC PHỨC HỢP (Observation & Assembly) — 85 ĐỘNG TỪ
# ==============================================================================

# 1. Quan sát, Đo lường & Phân tích (25 từ)
n4_quan_sat = [
    ("soi", ["soi kính", "chiếu rọi"], "OBSERVATION_ASSEMBLY", ["science", "optics", "microscopy"], "MICROSCOPE_INSPECT",
     "SCALE_REVEAL", [0.0, 1.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.2,
     [{"id": "reticle_crosshair", "description": "optical measurement grid reticle", "prompt": "circular brass optical reticle crosshair", "scale": 0.32}]),
    ("chiếu", ["rọi tia", "chiếu tia"], "OBSERVATION_ASSEMBLY", ["optics", "physics"], "PROJECT_BEAM",
     "SCALE_REVEAL", [0.0, 1.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.2, []),
    ("quét", ["quét cảm biến", "quét laser"], "OBSERVATION_ASSEMBLY", ["technology", "radar", "archaeology"], "LIDAR_SCAN",
     "SCAN_SWEEP", [1.0, 0.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.25,
     [{"id": "scan_line", "description": "laser horizontal scanning beam line", "prompt": "cyan fluorescent laser scan line bar", "scale": 0.3}]),
    ("quét qua", ["lia máy", "quét nhanh"], "OBSERVATION_ASSEMBLY", ["robotics", "optics"], "SWEEP_HORIZON",
     "SCAN_SWEEP", [1.0, 0.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.2, []),
    ("ngắm", ["ngắm nhìn", "ngắm bắn"], "OBSERVATION_ASSEMBLY", ["optics", "general"], "AIM_SIGHT",
     "HOLD_JITTER", [0.0, 0.0], 3, "HOLD_JITTER", "NONE", 1.0, 1.0, 1, 0.2, []),
    ("nhìn", ["trông", "quan sát bằng mắt"], "OBSERVATION_ASSEMBLY", ["general"], "LOOK_GAZE",
     "HOLD_JITTER", [0.0, 0.0], 3, "HOLD_JITTER", "NONE", 1.0, 1.0, 1, 0.2, []),
    ("quan sát", ["theo dõi", "giám sát kỹ"], "OBSERVATION_ASSEMBLY", ["scientific_method", "astronomy"], "OBSERVE_SCRUTINIZE",
     "SCALE_REVEAL", [0.0, 0.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.25, []),
    ("theo dõi", ["canh chừng", "bám sát"], "OBSERVATION_ASSEMBLY", ["biology", "security"], "TRACK_MONITOR",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.25, []),
    ("giám sát", ["thanh tra", "kiểm sát"], "OBSERVATION_ASSEMBLY", ["industry", "management"], "SUPERVISE_OVERSEE",
     "HOLD_JITTER", [0.0, 0.0], 3, "HOLD_JITTER", "NONE", 1.0, 1.0, 1, 0.2, []),
    ("đo", ["đo đạc", "đo lường"], "OBSERVATION_ASSEMBLY", ["metrology", "physics"], "GAUGE_MEASURE",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.2,
     [{"id": "caliper_ruler", "description": "vintage brass vernier caliper rule", "prompt": "antique brass measurement caliper ruler", "scale": 0.28}]),
    ("đo đạc", ["khảo sát trắc địa"], "OBSERVATION_ASSEMBLY", ["geodesy", "cartography"], "SURVEY_TRIANGULATE",
     "SCAN_SWEEP", [1.0, 0.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.25, []),
    ("cân", ["cân đo", "cân trọng lượng"], "OBSERVATION_ASSEMBLY", ["physics", "trade"], "WEIGH_SCALE",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 3, "PHYSICAL_BOUNCE", "SQUASH_AND_STRETCH", 1.05, 0.95, 2, 0.2,
     [{"id": "pan_scales", "description": "antique brass balance pan scales", "prompt": "antique justice balance pan scales brass", "scale": 0.32}]),
    ("đong", ["đong đếm", "đo thể tích"], "OBSERVATION_ASSEMBLY", ["chemistry", "pharmacy"], "VOLUMETRIC_FLASK",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.2, []),
    ("đếm", ["tính đếm", "liệt kê"], "OBSERVATION_ASSEMBLY", ["mathematics", "statistics"], "ENUMERATE_TALLY",
     "HOLD_JITTER", [0.0, 0.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.15, []),
    ("tính toán", ["giải toán", "ước lượng"], "OBSERVATION_ASSEMBLY", ["mathematics", "astronomy"], "COMPUTE_SOLVE",
     "HOLD_JITTER", [0.0, 0.0], 4, "HOLD_JITTER", "NONE", 1.0, 1.0, 1, 0.25, []),
    ("phóng to", ["phóng đại", "zoom in"], "OBSERVATION_ASSEMBLY", ["microscopy", "photography"], "MAGNIFY_ZOOM",
     "SCALE_REVEAL", [0.0, 0.0], 3, "PHYSICAL_BOUNCE", "PULSE_EXPAND", 1.35, 1.35, 3, 0.2, []),
    ("thu nhỏ", ["thu hẹp", "zoom out"], "OBSERVATION_ASSEMBLY", ["cartography", "optics"], "MINIFY_SCALE_DOWN",
     "SQUASH_AND_STRETCH", [0.0, 0.0], 3, "LINEAR_STEP", "SQUASH_AND_STRETCH", 0.75, 0.75, 3, 0.2, []),
    ("giải mã", ["đọc mã", "dịch chữ tượng hình"], "OBSERVATION_ASSEMBLY", ["archaeology", "cryptography"], "DECIPHER_DECODE",
     "SCAN_SWEEP", [1.0, 0.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.25,
     [{"id": "rosetta_tablet", "description": "ancient stone slab with hieroglyphs", "prompt": "antique black stone slab hieroglyphic inscription", "scale": 0.3}]),
    ("phân tích", ["mổ xẻ", "giải tích"], "OBSERVATION_ASSEMBLY", ["chemistry", "data_science"], "ASSAY_ANALYZE",
     "SCAN_SWEEP", [0.0, 1.0], 4, "LINEAR_STEP", "SPLIT_HALF", 1.1, 0.9, 2, 0.25, []),
    ("phát hiện", ["tìm ra", "khám phá thấy"], "OBSERVATION_ASSEMBLY", ["detective", "medicine"], "DETECT_DISCOVER",
     "SCALE_REVEAL", [0.0, 0.0], 2, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.15, []),
    ("tầm soát", ["sàng lọc", "kiểm tra diện rộng"], "OBSERVATION_ASSEMBLY", ["medicine", "epidemiology"], "SCREEN_PROBE",
     "SCAN_SWEEP", [1.0, 0.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.25, []),
    ("định vị", ["xác định tọa độ", "định vị GPS"], "OBSERVATION_ASSEMBLY", ["navigation", "geography"], "GEO_LOCATE",
     "SCALE_REVEAL", [0.0, 0.0], 3, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.2,
     [{"id": "astrolabe", "description": "antique brass mariner astrolabe navigational ring", "prompt": "ancient brass navigational astrolabe instrument", "scale": 0.28}]),
    ("kiểm tra", ["rà soát", "kiểm định"], "OBSERVATION_ASSEMBLY", ["quality_control", "engineering"], "AUDIT_VERIFY",
     "SCAN_SWEEP", [0.0, 1.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.2, []),
    ("nghiệm thu", ["đánh giá đạt chuẩn"], "OBSERVATION_ASSEMBLY", ["engineering", "software"], "ACCEPTANCE_PASS",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 2, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.15,
     [{"id": "green_stamp_passed", "description": "green certified quality assurance stamp", "prompt": "vintage green rubber approved stamp seal mark", "scale": 0.25}]),
    ("tra cứu", ["tìm kiếm hồ sơ", "lục tìm"], "OBSERVATION_ASSEMBLY", ["archives", "library"], "INDEX_LOOKUP",
     "SEQUENTIAL_SPAWN", [0.0, 1.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.2, [])
]

# 2. Biến đổi Hóa sinh & Nhiệt động lực (26 từ)
n4_hoa_sinh = [
    ("đốt cháy", ["thiêu rụi", "châm lửa"], "OBSERVATION_ASSEMBLY", ["chemistry", "combustion"], "IGNITE_INCINERATE",
     "PULSE_EXPAND", [0.0, -1.0], 3, "PHYSICAL_BOUNCE", "SHRINK_AND_DISAPPEAR", 0.7, 0.7, 3, 0.2,
     [{"id": "flame_tongues", "description": "stylized orange fire flame tongues", "prompt": "vintage graphic bright orange flame tongues cutout", "scale": 0.3}]),
    ("cháy", ["bốc hỏa", "rực lửa"], "OBSERVATION_ASSEMBLY", ["thermodynamics"], "BURN_COMBUST",
     "HOLD_JITTER", [0.0, -1.0], 4, "HOLD_JITTER", "SHRINK_AND_DISAPPEAR", 0.8, 0.8, 3, 0.25, []),
    ("nung", ["nung đỏ", "nung gốm"], "OBSERVATION_ASSEMBLY", ["metallurgy", "ceramics"], "KILN_SMELT",
     "PULSE_EXPAND", [0.0, 0.0], 4, "LINEAR_STEP", "SQUASH_AND_STRETCH", 1.05, 1.05, 3, 0.25, []),
    ("thiêu", ["thiêu đốt", "hỏa thiêu"], "OBSERVATION_ASSEMBLY", ["history", "warfare"], "CREMATE_BLAZE",
     "PULSE_EXPAND", [0.0, 0.0], 3, "PHYSICAL_BOUNCE", "SHRINK_AND_DISAPPEAR", 0.6, 0.6, 3, 0.2, []),
    ("đun sôi", ["sôi sùng sục", "nấu sôi"], "OBSERVATION_ASSEMBLY", ["chemistry", "thermodynamics"], "BOIL_EBULLITION",
     "HOLD_JITTER", [0.0, -1.0], 4, "HOLD_JITTER", "NONE", 1.0, 1.0, 1, 0.25,
     [{"id": "steam_wisps", "description": "wisps of white evaporative steam", "prompt": "curling translucent white vapor steam plumes", "scale": 0.3}]),
    ("đóng băng", ["hóa đá", "đông lạnh"], "OBSERVATION_ASSEMBLY", ["cryogenics", "meteorology"], "FREEZE_SOLIDIFY",
     "SQUASH_AND_STRETCH", [0.0, 0.0], 3, "PHYSICAL_BOUNCE", "CRACK", 1.1, 1.1, 3, 0.25,
     [{"id": "ice_crystals", "description": "sharp geometric ice frost crystals", "prompt": "hexagonal frost ice crystal shards frost", "scale": 0.3}]),
    ("tan chảy", ["nóng chảy", "rã đông"], "OBSERVATION_ASSEMBLY", ["thermodynamics", "metallurgy"], "MELT_LIQUEFY",
     "SQUASH_AND_STRETCH", [0.0, 1.0], 4, "LINEAR_STEP", "SQUASH_AND_STRETCH", 1.35, 0.5, 4, 0.25, []),
    ("kết tinh", ["tạo tinh thể", "đọng muối"], "OBSERVATION_ASSEMBLY", ["chemistry", "mineralogy"], "CRYSTALLIZE",
     "SCALE_REVEAL", [0.0, 0.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.25,
     [{"id": "mineral_geode", "description": "sparkling quartz geode crystal cluster", "prompt": "sparkling purple quartz geode crystal mineral", "scale": 0.3}]),
    ("đông đặc", ["ngưng kết", "đông kết"], "OBSERVATION_ASSEMBLY", ["physics", "polymer"], "CONGEAL_SET",
     "SQUASH_AND_STRETCH", [0.0, 0.0], 3, "LINEAR_STEP", "SQUASH_AND_STRETCH", 0.95, 0.95, 2, 0.2, []),
    ("ngưng tụ", ["đọng sương", "ngưng kết hơi"], "OBSERVATION_ASSEMBLY", ["meteorology", "physics"], "CONDENSE_PRECIPITATE",
     "SEQUENTIAL_SPAWN", [0.0, 1.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.2, []),
    ("hóa hơi", ["bay hơi", "thăng hoa"], "OBSERVATION_ASSEMBLY", ["thermodynamics"], "EVAPORATE_VAPORIZE",
     "DISCRETE_TRANSLATE", [0.0, -1.0], 4, "LINEAR_STEP", "SHRINK_AND_DISAPPEAR", 0.5, 0.5, 3, 0.3, []),
    ("bốc khói", ["nhả khói", "nghi ngút khói"], "OBSERVATION_ASSEMBLY", ["combustion", "general"], "FUME_SMOLDER",
     "SEQUENTIAL_SPAWN", [0.0, -1.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.25, []),
    ("phân hủy", ["tiêu hủy", "phân rã"], "OBSERVATION_ASSEMBLY", ["biology", "ecology"], "DECOMPOSE_DECAY",
     "SQUASH_AND_STRETCH", [0.0, 0.0], 4, "HOLD_JITTER", "SHRINK_AND_DISAPPEAR", 0.65, 0.65, 4, 0.3, []),
    ("mục rữa", ["mủn ra", "mục nát"], "OBSERVATION_ASSEMBLY", ["ecology", "archaeology"], "ROT_PUTREFY",
     "SQUASH_AND_STRETCH", [0.0, 0.0], 4, "HOLD_JITTER", "CRACK", 0.8, 0.8, 3, 0.25, []),
    ("thối rữa", ["rữa nát", "phân hủy bốc mùi"], "OBSERVATION_ASSEMBLY", ["microbiology"], "PUTREFACTION",
     "HOLD_JITTER", [0.0, 0.0], 4, "HOLD_JITTER", "SHRINK_AND_DISAPPEAR", 0.7, 0.7, 3, 0.25, []),
    ("lên men", ["ủ men", "chuyển hóa men"], "OBSERVATION_ASSEMBLY", ["biochemistry", "food_tech"], "FERMENTATION",
     "PULSE_EXPAND", [0.0, 0.0], 4, "HOLD_JITTER", "NONE", 1.0, 1.0, 1, 0.25,
     [{"id": "ferment_bubbles", "description": "fermentation yeast carbonation foam", "prompt": "yeast fermentation foam bubbles yeast", "scale": 0.25}]),
    ("rỉ sét", ["ăn mòn kim loại", "hoen rỉ"], "OBSERVATION_ASSEMBLY", ["metallurgy", "chemistry"], "OXIDIZE_RUST",
     "PULSE_EXPAND", [0.0, 0.0], 4, "LINEAR_STEP", "CRACK", 1.0, 1.0, 2, 0.25,
     [{"id": "rust_flakes", "description": "flaking red iron oxide rust texture", "prompt": "flaking reddish brown iron rust texture patch", "scale": 0.28}]),
    ("oxy hóa", ["bị oxy hóa", "cháy chậm"], "OBSERVATION_ASSEMBLY", ["chemistry"], "OXIDATION_REACTION",
     "PULSE_EXPAND", [0.0, 0.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.2, []),
    ("hóa thạch", ["hóa đá sinh vật", "chôn vùi ngàn năm"], "OBSERVATION_ASSEMBLY", ["paleontology", "geology"], "FOSSILIZE_PETRIFY",
     "SQUASH_AND_STRETCH", [0.0, 0.0], 4, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.3,
     [{"id": "ammonite_shell", "description": "petrified ammonite spiral fossil", "prompt": "antique petrified spiral ammonite shell fossil", "scale": 0.3}]),
    ("biến dị", ["dị tật di truyền", "biến hình"], "OBSERVATION_ASSEMBLY", ["genetics", "evolution"], "MUTATE_VARIATION",
     "PULSE_EXPAND", [0.0, 0.0], 3, "PHYSICAL_BOUNCE", "SQUASH_AND_STRETCH", 1.25, 0.8, 3, 0.2, []),
    ("đột biến", ["đột biến gen", "biến dị ngẫu nhiên"], "OBSERVATION_ASSEMBLY", ["genetics", "molecular_biology"], "GENE_MUTATION",
     "PULSE_EXPAND", [0.0, 0.0], 3, "PHYSICAL_BOUNCE", "SQUASH_AND_STRETCH", 1.2, 0.85, 3, 0.2, []),
    ("tiến hóa", ["chọn lọc tự nhiên", "phát triển loài"], "OBSERVATION_ASSEMBLY", ["evolutionary_biology"], "EVOLVE_ADAPT",
     "SCALE_REVEAL", [0.0, 0.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.3, []),
    ("biến đổi", ["thay đổi cấu trúc", "chuyển hóa"], "OBSERVATION_ASSEMBLY", ["general", "chemistry"], "METAMORPHOSE_ALTER",
     "PULSE_EXPAND", [0.0, 0.0], 3, "LINEAR_STEP", "SQUASH_AND_STRETCH", 1.1, 1.1, 2, 0.2, []),
    ("già cỗi", ["lão hóa", "suy tàn"], "OBSERVATION_ASSEMBLY", ["biology", "gerontology"], "SENESCENCE_AGE",
     "SQUASH_AND_STRETCH", [0.0, 1.0], 4, "LINEAR_STEP", "SQUASH_AND_STRETCH", 0.85, 0.85, 3, 0.3, []),
    ("trẻ hóa", ["tái sinh tế bào", "phục hồi"], "OBSERVATION_ASSEMBLY", ["medicine", "cosmetics"], "REJUVENATE_RESTORE",
     "SCALE_REVEAL", [0.0, 0.0], 3, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.2, []),
    ("tái sinh", ["hồi sinh", "phục sinh"], "OBSERVATION_ASSEMBLY", ["biology", "mythology"], "REGENERATE_REVIVE",
     "PULSE_EXPAND", [0.0, 0.0], 3, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.2, [])
]

# 3. Lắp ráp, Chế tác & Nghi lễ Khảo cổ (20 từ)
n4_lap_rap = [
    ("xây dựng", ["kiến thiết", "dựng nên"], "OBSERVATION_ASSEMBLY", ["architecture", "civil_engineering"], "CONSTRUCT_BUILD",
     "DISCRETE_TRANSLATE", [0.0, -1.0], 4, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.25,
     [{"id": "masonry_blocks", "description": "cut sandstone megalithic building blocks", "prompt": "stacked ancient sandstone pyramid building blocks", "scale": 0.32}]),
    ("lắp ráp", ["lắp ghép", "chắp nối"], "OBSERVATION_ASSEMBLY", ["mechanics", "manufacturing"], "ASSEMBLE_FIT",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 3, "PHYSICAL_BOUNCE", "SQUASH_AND_STRETCH", 1.05, 0.95, 2, 0.2, []),
    ("ghép", ["chắp", "nối kết"], "OBSERVATION_ASSEMBLY", ["carpentry", "craft"], "MORTISE_TENON",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 2, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.15, []),
    ("dán", ["dán hồ", "dán keo"], "OBSERVATION_ASSEMBLY", ["craft", "general"], "GLUE_AFFIX",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 2, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.15, []),
    ("gắn", ["đính", "gắn kết"], "OBSERVATION_ASSEMBLY", ["craft", "mechanics"], "FASTEN_MOUNT",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 2, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.15, []),
    ("đắp", ["đắp đất", "bồi đắp"], "OBSERVATION_ASSEMBLY", ["sculpture", "geology"], "MOUND_SCULPT",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 3, "LINEAR_STEP", "SQUASH_AND_STRETCH", 1.15, 0.9, 2, 0.2, []),
    ("đúc", ["đúc đồng", "rót khuôn"], "OBSERVATION_ASSEMBLY", ["metallurgy", "foundry"], "CAST_MOLD",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 3, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.25,
     [{"id": "bronze_crucible", "description": "antique ceramic crucible with glowing molten bronze", "prompt": "clay crucible pouring molten golden bronze", "scale": 0.28}]),
    ("điêu khắc", ["tạc tượng", "đục đẽo nghệ thuật"], "OBSERVATION_ASSEMBLY", ["sculpture", "art"], "SCULPT_CHISEL",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 3, "PHYSICAL_BOUNCE", "CRACK", 1.05, 0.95, 2, 0.2, []),
    ("chạm trổ", ["chạm khắc", "khắc họa hoa văn"], "OBSERVATION_ASSEMBLY", ["fine_art", "craft"], "ENGRAVE_CARVE",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.2, []),
    ("ướp xác", ["bảo quản thi thể", "ướp xác Ai Cập"], "OBSERVATION_ASSEMBLY", ["archaeology", "egyptology", "history"], "EMBALM_MUMMIFY",
     "SEQUENTIAL_SPAWN", [0.0, 1.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.3,
     [{"id": "linen_wrapping", "description": "aged ancient linen mummy wrapping band", "prompt": "aged antique linen mummy shroud bandage ribbon", "scale": 0.3}]),
    ("quấn băng", ["băng bó", "quấn vải lanh"], "OBSERVATION_ASSEMBLY", ["egyptology", "medicine"], "SWATHE_BANDAGE",
     "SQUASH_AND_STRETCH", [1.0, 0.0], 3, "LINEAR_STEP", "SQUASH_AND_STRETCH", 0.9, 1.1, 2, 0.2, []),
    ("đặt vào quan tài", ["nhập quan", "đặt vào quách", "vào quan tài", "quan tài"], "OBSERVATION_ASSEMBLY", ["archaeology", "egyptology"], "ENTOMB_SARCOPHAGUS",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 3, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.25,
     [{"id": "pharaoh_mask", "description": "golden funerary death mask", "prompt": "ornate gold pharaoh death mask ancient Egypt", "scale": 0.32}]),
    ("chôn cất", ["mai táng", "an táng"], "OBSERVATION_ASSEMBLY", ["anthropology", "history"], "INTERMENT_BURY",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 4, "LINEAR_STEP", "SHRINK_AND_DISAPPEAR", 0.8, 0.8, 3, 0.3, []),
    ("phong ấn", ["niêm phong", "khóa ấn"], "OBSERVATION_ASSEMBLY", ["history", "archaeology"], "SEAL_CONSECRATE",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 2, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.15,
     [{"id": "clay_cartouche_seal", "description": "clay hieroglyphic cartouche seal", "prompt": "ancient Egyptian clay cartouche seal imprint", "scale": 0.25}]),
    ("khai quật", ["đào bới khảo cổ", "phát lộ cổ vật"], "OBSERVATION_ASSEMBLY", ["archaeology", "paleontology"], "EXCAVATE_UNEARTH",
     "DISCRETE_TRANSLATE", [0.0, -1.0], 4, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.3,
     [{"id": "trowel_brush", "description": "archaeological spade trowel and dust brush", "prompt": "archaeologist field hand trowel and brush", "scale": 0.25}]),
    ("thờ phụng", ["cúng bái", "chiêm bái"], "OBSERVATION_ASSEMBLY", ["religion", "anthropology"], "VENERATE_WORSHIP",
     "HOLD_JITTER", [0.0, 0.0], 3, "HOLD_JITTER", "NONE", 1.0, 1.0, 1, 0.2, []),
    ("tôn vinh", ["ca tụng", "vinh danh"], "OBSERVATION_ASSEMBLY", ["history", "sociology"], "EXALT_GLORIFY",
     "SCALE_REVEAL", [0.0, -1.0], 3, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.2, []),
    ("đăng quang", ["lên ngôi", "thụ vương miện"], "OBSERVATION_ASSEMBLY", ["monarchy", "history"], "CORONATION_CROWN",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 3, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.25,
     [{"id": "gold_crown", "description": "jeweled royal golden monarch crown", "prompt": "ornate jeweled antique gold monarch royal crown", "scale": 0.28}]),
    ("thoái vị", ["nhường ngôi", "từ chức"], "OBSERVATION_ASSEMBLY", ["history", "politics"], "ABDICATE_RELINQUISH",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.25, []),
    ("ký kết", ["ký hòa ước", "đặt bút ký"], "OBSERVATION_ASSEMBLY", ["diplomacy", "history"], "SIGN_RATIFY",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.2,
     [{"id": "quill_parchment", "description": "feather ink quill and rolled treaty scroll", "prompt": "vintage ink quill pen writing on parchment treaty", "scale": 0.28}]),
]

# 4. Vây bắt, Giam cầm & Đối kháng (14 từ)
n4_vay_bat = [
    ("vươn xúc tu", ["vươn vòi", "vươn dài"], "OBSERVATION_ASSEMBLY", ["marine_biology", "zoology"], "EXTEND_TENTACLE",
     "SEQUENTIAL_SPAWN", [0.0, 1.0], 4, "PHYSICAL_BOUNCE", "SQUASH_AND_STRETCH", 0.9, 1.1, 2, 0.25,
     [{"id": "tentacle_arms", "description": "curling octopus suction tentacle arms", "prompt": "coiling deep ocean kraken octopus tentacle arm", "scale": 0.35}]),
    ("bao vây", ["quây kín", "khép vòng vây"], "OBSERVATION_ASSEMBLY", ["military", "cell_biology"], "BESIEGE_ENCIRCLE",
     "PULSE_EXPAND", [0.0, 0.0], 4, "LINEAR_STEP", "SQUASH_AND_STRETCH", 0.85, 0.85, 3, 0.25, []),
    ("bao bọc", ["che chở", "ôm lấy"], "OBSERVATION_ASSEMBLY", ["biology", "general"], "ENVELOPE_WRAP",
     "PULSE_EXPAND", [0.0, 0.0], 3, "PHYSICAL_BOUNCE", "SQUASH_AND_STRETCH", 0.9, 0.9, 2, 0.2, []),
    ("nuốt chửng", ["thực bào", "nuốt trọn"], "OBSERVATION_ASSEMBLY", ["cell_biology", "zoology"], "ENGULF_PHAGOCYTE",
     "SCALE_REVEAL", [0.0, 0.0], 4, "PHYSICAL_BOUNCE", "SHRINK_AND_DISAPPEAR", 0.5, 0.5, 4, 0.3,
     [{"id": "lysosome_vesicles", "description": "enzymatic digestive lysosome spheres", "prompt": "microscopic digestive lysosome enzyme vesicles", "scale": 0.25}]),
    ("giam cầm", ["nhốt tù", "cầm tù"], "OBSERVATION_ASSEMBLY", ["history", "jurisprudence"], "INCARCERATE_IMPRISON",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 3, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.2,
     [{"id": "iron_bars", "description": "heavy cast iron dungeon prison grates", "prompt": "antique rusted iron dungeon cell bars grate", "scale": 0.35}]),
    ("nhốt", ["nhốt vào lồng", "giam"], "OBSERVATION_ASSEMBLY", ["zoology", "general"], "CAGE_CONFINE",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 3, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.2, []),
    ("trói buộc", ["thắt dây", "cột chặt"], "OBSERVATION_ASSEMBLY", ["general"], "BIND_TETHER",
     "SQUASH_AND_STRETCH", [0.0, 0.0], 3, "LINEAR_STEP", "SQUASH_AND_STRETCH", 0.85, 0.85, 2, 0.2, []),
    ("phong tỏa", ["cấm vận", "khóa chặt"], "OBSERVATION_ASSEMBLY", ["military", "geopolitics"], "BLOCKADE_SEAL",
     "DISCRETE_TRANSLATE", [0.0, 0.0], 3, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.2, []),
    ("đối đầu", ["chạm trán", "giáp mặt"], "OBSERVATION_ASSEMBLY", ["warfare", "general"], "CONFRONT_FACE",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 3, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.15, []),
    ("giao chiến", ["đánh trận", "ác chiến"], "OBSERVATION_ASSEMBLY", ["warfare", "history"], "SKIRMISH_CLASH",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 4, "PHYSICAL_BOUNCE", "CRACK", 1.1, 0.9, 2, 0.2, []),
    ("chống trả", ["kháng cự", "đáp trả"], "OBSERVATION_ASSEMBLY", ["immunology", "warfare"], "RESIST_DEFEND",
     "DISCRETE_TRANSLATE", [-1.0, 0.0], 3, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.15, []),
    ("đẩy lùi", ["đánh lui", "đẩy ra xa"], "OBSERVATION_ASSEMBLY", ["warfare", "physics"], "REPEL_DRIVE_BACK",
     "DISCRETE_TRANSLATE", [-1.0, 0.0], 3, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 2, 0.2, []),
    ("giằng co", ["tranh chấp", "đấu lực"], "OBSERVATION_ASSEMBLY", ["sports", "warfare"], "STALEMATE_TUG",
     "HOLD_JITTER", [1.0, 0.0], 4, "HOLD_JITTER", "NONE", 1.0, 1.0, 1, 0.2, []),
    ("lật đổ", ["lật nhào", "đảo chính"], "OBSERVATION_ASSEMBLY", ["history", "politics"], "OVERTHROW_TOPPLE",
     "DISCRETE_TRANSLATE", [1.0, 1.0], 3, "PHYSICAL_BOUNCE", "CRACK", 1.25, 0.75, 3, 0.2, [])
]

# Nạp nhóm 4
for item in (n4_quan_sat + n4_hoa_sinh + n4_lap_rap + n4_vay_bat):
    add_verb(*item)

# ==============================================================================
# NHÓM 5: SINH LÝ NGƯỜI (Human Physiology) — Stage 6 mở rộng
# Động từ cốt lõi của video y học / sinh học cơ thể người, ánh xạ sang
# beat_action của story beats để mọi video diễn đồng nhất.
# ==============================================================================
n5_tim_mach = [
    ("bơm", ["bơm máu"], "PHYSIOLOGY_VITAL", ["cardiology", "physiology"], "PUMP_PRESSURE",
     "SQUASH_AND_STRETCH", [0.0, 0.0], 2, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.0, [],
     False, 1.5, "pulse"),
    ("tim đập", ["đập thình thịch", "đập rộn ràng"], "PHYSIOLOGY_VITAL", ["cardiology", "physiology"], "HEARTBEAT_PULSE",
     "SQUASH_AND_STRETCH", [0.0, 0.0], 2, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.0, [],
     False, 1.5, "pulse"),
    ("co bóp", ["bóp nhịp nhàng", "co bóp nhịp nhàng"], "PHYSIOLOGY_VITAL", ["cardiology", "physiology", "gastroenterology"], "RHYTHMIC_CONTRACTION",
     "SQUASH_AND_STRETCH", [0.0, 0.0], 2, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.0, [],
     False, 1.5, "pulse"),
    ("đập nhanh", ["tim đập nhanh", "đập dồn dập"], "PHYSIOLOGY_VITAL", ["cardiology"], "TACHYCARDIA_RAPID",
     "SQUASH_AND_STRETCH", [0.0, 0.0], 2, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.0, [],
     False, 1.5, "pulse"),
    ("tuần hoàn", ["lưu thông", "máu lưu thông"], "PHYSIOLOGY_VITAL", ["cardiology", "physiology"], "BLOOD_CIRCULATION",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.0, [],
     False, 1.5, "flow"),
    ("máu chảy", ["dòng máu chảy"], "PHYSIOLOGY_VITAL", ["cardiology", "physiology"], "BLOOD_FLOW",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.0, [],
     False, 1.5, "flow"),
    ("đông máu", ["đông lại", "máu đông"], "PHYSIOLOGY_VITAL", ["hematology", "medicine"], "CLOT_FORMATION",
     "DISCRETE_TRANSLATE", [0.0, 0.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.0, [],
     False, 1.5, "block"),
    ("tắc mạch", ["tắc nghẽn", "nghẽn mạch"], "PHYSIOLOGY_VITAL", ["cardiology", "medicine"], "VESSEL_OCCLUSION",
     "DISCRETE_TRANSLATE", [0.0, 0.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.0, [],
     False, 1.5, "block"),
    ("vỡ mạch", ["vỡ mạch máu"], "PHYSIOLOGY_VITAL", ["cardiology", "medicine"], "VESSEL_RUPTURE",
     "DISCRETE_TRANSLATE", [0.0, 0.0], 3, "PHYSICAL_BOUNCE", "CRACK", 1.2, 0.8, 2, 0.2, [],
     True, 1.5, "divide"),
]

n5_ho_hap = [
    ("thở", ["hít thở"], "PHYSIOLOGY_VITAL", ["pulmonology", "physiology"], "BREATH_CYCLE",
     "SQUASH_AND_STRETCH", [0.0, 0.0], 2, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.0, [],
     False, 1.5, "pulse"),
    ("hít vào", ["hít khí"], "PHYSIOLOGY_VITAL", ["pulmonology"], "INHALE_FLOW",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.0, [],
     False, 1.5, "flow"),
    ("thở ra", ["thải khí"], "PHYSIOLOGY_VITAL", ["pulmonology"], "EXHALE_FLOW",
     "DISCRETE_TRANSLATE", [0.0, -1.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.0, [],
     False, 1.5, "flow"),
    ("trao đổi khí", ["trao đổi oxy"], "PHYSIOLOGY_VITAL", ["pulmonology", "physiology"], "GAS_EXCHANGE",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.0, [],
     False, 1.5, "flow"),
]

n5_tieu_hoa = [
    ("nuốt", ["nuốt chửng"], "PHYSIOLOGY_VITAL", ["gastroenterology", "physiology"], "SWALLOW_ENGULF",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 3, "PHYSICAL_BOUNCE", "SHRINK_AND_DISAPPEAR", 0.9, 0.9, 2, 0.2, [],
     False, 1.5, "absorb"),
    ("nhào trộn", ["nghiền thức ăn"], "PHYSIOLOGY_VITAL", ["gastroenterology"], "CHURN_MIX",
     "SQUASH_AND_STRETCH", [0.0, 0.0], 3, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.0, [],
     False, 1.5, "pulse"),
    ("tiêu hóa", ["phân giải thức ăn"], "PHYSIOLOGY_VITAL", ["gastroenterology"], "DIGEST_DISSOLVE",
     "DISCRETE_TRANSLATE", [0.0, 0.0], 3, "LINEAR_STEP", "SHRINK_AND_DISAPPEAR", 0.9, 0.9, 3, 0.3, [],
     False, 1.5, "absorb"),
    ("hấp thụ", ["hấp thu"], "PHYSIOLOGY_VITAL", ["gastroenterology", "physiology"], "ABSORB_UPTAKE",
     "DISCRETE_TRANSLATE", [0.0, 0.0], 3, "LINEAR_STEP", "SHRINK_AND_DISAPPEAR", 0.9, 0.9, 3, 0.3, [],
     False, 1.5, "absorb"),
    ("đẩy thức ăn", ["nhu động ruột"], "PHYSIOLOGY_VITAL", ["gastroenterology"], "PERISTALSIS_WAVE",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.0, [],
     False, 1.5, "flow"),
]

n5_bai_tiet = [
    ("lọc máu", ["lọc"], "PHYSIOLOGY_VITAL", ["nephrology", "physiology"], "FILTER_FLOW",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.0, [],
     False, 1.5, "flow"),
    ("thải độc", ["đào thải"], "PHYSIOLOGY_VITAL", ["nephrology", "medicine"], "DETOX_EXPEL",
     "DISCRETE_TRANSLATE", [0.0, 1.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.0, [],
     False, 1.5, "exit"),
    ("thải", ["thải ra"], "PHYSIOLOGY_VITAL", ["physiology", "general"], "EXCRETE_RELEASE",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.0, [],
     False, 1.5, "exit"),
]

n5_than_kinh = [
    ("dẫn truyền", ["truyền tín hiệu"], "PHYSIOLOGY_VITAL", ["neurology", "physiology"], "NERVE_CONDUCT",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.0, [],
     False, 1.5, "flow"),
    ("lan truyền", ["lan tỏa"], "PHYSIOLOGY_VITAL", ["neurology", "general"], "SIGNAL_SPREAD",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.0, [],
     False, 1.5, "flow"),
    ("phát tín hiệu thần kinh", ["báo động"], "PHYSIOLOGY_VITAL", ["neurology", "immunology"], "SIGNAL_EMIT",
     "SQUASH_AND_STRETCH", [0.0, 0.0], 2, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.0, [],
     False, 1.5, "emphasize"),
]

n5_mien_dich = [
    ("bảo vệ", ["che chắn"], "PHYSIOLOGY_VITAL", ["immunology", "medicine"], "DEFEND_BLOCK",
     "DISCRETE_TRANSLATE", [0.0, 0.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.0, [],
     False, 1.5, "block"),
    ("viêm", ["sưng viêm"], "PHYSIOLOGY_VITAL", ["immunology", "medicine"], "INFLAME_SWELL",
     "SQUASH_AND_STRETCH", [0.0, 0.0], 3, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.0, [],
     False, 1.5, "emphasize"),
    ("sưng", ["phồng"], "PHYSIOLOGY_VITAL", ["immunology", "general"], "SWELL_GROW",
     "SQUASH_AND_STRETCH", [0.0, 0.0], 3, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.0, [],
     False, 1.5, "emphasize"),
]

n5_chung = [
    ("co cơ", ["co lại"], "PHYSIOLOGY_VITAL", ["physiology", "sports"], "MUSCLE_CONTRACT",
     "SQUASH_AND_STRETCH", [0.0, 0.0], 3, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.0, [],
     False, 1.5, "emphasize"),
    ("vận chuyển", ["chở"], "PHYSIOLOGY_VITAL", ["physiology", "hematology"], "TRANSPORT_CARRY",
     "DISCRETE_TRANSLATE", [1.0, 0.0], 4, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.0, [],
     False, 1.5, "flow"),
    ("lành", ["hồi phục"], "PHYSIOLOGY_VITAL", ["medicine", "general"], "HEAL_RESTORE",
     "SQUASH_AND_STRETCH", [0.0, 0.0], 2, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.0, [],
     False, 1.5, "emphasize"),
    ("chết dần", ["tế bào chết"], "PHYSIOLOGY_VITAL", ["cell_biology", "medicine"], "APOPTOSIS_FADE",
     "DISCRETE_TRANSLATE", [0.0, 0.0], 3, "LINEAR_STEP", "SHRINK_AND_DISAPPEAR", 0.9, 0.9, 3, 0.3, [],
     False, 1.5, "absorb"),
    ("mọc", ["mọc lên"], "PHYSIOLOGY_VITAL", ["physiology", "general"], "GROW_SPROUT",
     "SCALE_REVEAL", [0.0, 0.0], 3, "PHYSICAL_BOUNCE", "NONE", 1.0, 1.0, 1, 0.0, [],
     False, 1.5, "enter"),
    ("ngấm", ["thấm"], "PHYSIOLOGY_VITAL", ["pharmacology", "general"], "SOAK_ABSORB",
     "DISCRETE_TRANSLATE", [0.0, 0.0], 3, "LINEAR_STEP", "SHRINK_AND_DISAPPEAR", 0.95, 0.95, 3, 0.3, [],
     False, 1.5, "absorb"),
    ("tiết ra", ["tiết hormone"], "PHYSIOLOGY_VITAL", ["endocrinology", "physiology"], "SECRETE_RELEASE",
     "DISCRETE_TRANSLATE", [0.0, -1.0], 3, "LINEAR_STEP", "NONE", 1.0, 1.0, 1, 0.0, [],
     False, 1.5, "flow"),
    ("run rẩy", ["run"], "PHYSIOLOGY_VITAL", ["general", "physiology"], "TREMBLE_SHAKE",
     "HOLD_JITTER", [0.0, 0.0], 4, "HOLD_JITTER", "NONE", 1.0, 1.0, 1, 0.0, [],
     False, 1.5, "emphasize"),
]

# Nạp nhóm 5
for item in (n5_tim_mach + n5_ho_hap + n5_tieu_hoa + n5_bai_tiet + n5_than_kinh + n5_mien_dich + n5_chung):
    add_verb(*item)

# Gán beat_action cho các entry cũ còn thiếu (giữ nguyên mọi trường khác)
_BEAT_ACTION_PATCH = {
    "nuốt chửng": "absorb",   # synonym: thực bào
    "phân bào": "divide",
    "tiến công": "attack",     # synonym: tấn công
    "nhân đôi": "divide",
    "săn mồi": "approach",
}
for _entry in VERBS_DATA:
    if _entry["verb_vi"] in _BEAT_ACTION_PATCH and not _entry.get("beat_action"):
        _entry["beat_action"] = _BEAT_ACTION_PATCH[_entry["verb_vi"]]

# ==============================================================================
# LƯU VÀO FILE JSON
# ==============================================================================
print(f"Tổng số động từ được nạp: {len(VERBS_DATA)}")

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(VERBS_DATA, f, ensure_ascii=False, indent=2)

print(f"Đã lưu thành công vào: {OUTPUT_FILE}")
