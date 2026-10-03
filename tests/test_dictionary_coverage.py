"""
AutoVideoFactory — Test Dictionary Coverage (Phase 1)
Kiểm tra độ phủ và tính toàn vẹn của 325 động từ trong data/dictionaries/verb_kinetic_dictionary.json
"""

import sys
import json
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DICTIONARY_FILE = Path("data/dictionaries/verb_kinetic_dictionary.json")

REQUIRED_FIELDS = [
    "verb_vi",
    "synonyms",
    "category",
    "motion_type",
    "hero_behavior",
    "target_reaction"
]

CATEGORY_MIN_COUNTS = {
    "FORCE_DEFORMATION": 80,
    "EMISSION_SPAWNING": 75,
    "LOCOMOTION_NAVIGATION": 70,
    "OBSERVATION_ASSEMBLY": 80
}

def test_dictionary():
    print("=" * 70)
    print("🔍 [TEST] KIỂM THỬ ĐỘ PHỦ VÀ TÍNH TOÀN VẸN CỦA VERB KINETIC DICTIONARY")
    print("=" * 70)

    assert DICTIONARY_FILE.exists(), f"❌ Không tìm thấy file {DICTIONARY_FILE}"

    with open(DICTIONARY_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    total_count = len(data)
    print(f"📊 Tổng số lượng động từ đã mã hóa: {total_count}")
    assert total_count >= 320, f"❌ Số lượng động từ {total_count} nhỏ hơn yêu cầu (>= 320)!"

    category_counts = {
        "FORCE_DEFORMATION": 0,
        "EMISSION_SPAWNING": 0,
        "LOCOMOTION_NAVIGATION": 0,
        "OBSERVATION_ASSEMBLY": 0
    }

    errors = []
    seen_verbs = set()

    for idx, entry in enumerate(data, start=1):
        # 1. Kiểm tra trường bắt buộc
        for field in REQUIRED_FIELDS:
            if field not in entry:
                errors.append(f"Mục #{idx} ({entry.get('verb_vi', 'Unknown')}): Thiếu trường '{field}'")

        # 2. Kiểm tra verb_vi hợp lệ
        v_vi = entry.get("verb_vi", "").strip()
        if not v_vi:
            errors.append(f"Mục #{idx}: 'verb_vi' bị rỗng!")
        if v_vi in seen_verbs:
            errors.append(f"Mục #{idx}: Trùng lặp động từ '{v_vi}'!")
        seen_verbs.add(v_vi)

        # 3. Kiểm tra category
        cat = entry.get("category")
        if cat in category_counts:
            category_counts[cat] += 1
        else:
            errors.append(f"Mục #{idx} ('{v_vi}'): Category không hợp lệ: {cat}")

        # 4. Kiểm tra chi tiết hero_behavior và target_reaction
        hb = entry.get("hero_behavior", {})
        if not isinstance(hb, dict) or "action" not in hb:
            errors.append(f"Mục #{idx} ('{v_vi}'): 'hero_behavior' không hợp lệ")

        tr = entry.get("target_reaction", {})
        if not isinstance(tr, dict) or "action" not in tr:
            errors.append(f"Mục #{idx} ('{v_vi}'): 'target_reaction' không hợp lệ")

    print("\n📈 THỐNG KÊ CHI TIẾT THEO 4 NHÓM:")
    for cat, count in category_counts.items():
        min_req = CATEGORY_MIN_COUNTS.get(cat, 0)
        status = "✅ ĐẠT (PASS)" if count >= min_req else "❌ CHƯA ĐẠT (FAIL)"
        print(f"   - {cat:<25}: {count:>3} từ (Yêu cầu >= {min_req:>2}) -> {status}")
        assert count >= min_req, f"❌ Nhóm {cat} chỉ có {count} từ, nhỏ hơn yêu cầu {min_req}!"

    if errors:
        print(f"\n❌ Phát hiện {len(errors)} lỗi:")
        for err in errors[:10]:
            print(f"   - {err}")
        assert len(errors) == 0, "Kiểm thử thất bại do có lỗi dữ liệu!"

    print("\n✅ TẤT CẢ CÁC MỤC TỪ ĐỀU ĐẠT CHUẨN TOÀN VẸN 100% CẤU TRÚC JSON!")
    print("=" * 70)
    print(f"🎯 KẾT LUẬN: ĐÃ MÃ HÓA THÀNH CÔNG {total_count}/325 ĐỘNG TỪ TIẾNG VIỆT CỐT LÕI (100% ĐẠT)")
    print("=" * 70)

if __name__ == "__main__":
    test_dictionary()
