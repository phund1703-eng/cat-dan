"""
AutoVideoFactory — Test Semantic Matcher (Phase 2)
Kiểm thử bộ ánh xạ VerbSemanticMatcher trên 20 câu thoại thực tế đa lĩnh vực.
"""

import sys
import asyncio
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.script_engine.verb_semantic_matcher import VerbSemanticMatcher

TEST_SENTENCES = [
    {
        "id": 1,
        "domain": "Cơ khí",
        "sentence": "Chiếc máy ép khổng lồ dập mạnh xuống làm bẹp dúm thanh kim loại."
    },
    {
        "id": 2,
        "domain": "Sinh học",
        "sentence": "Các tế bào bạch cầu nhanh chóng vươn xúc tu bao vây cụm vi khuẩn."
    },
    {
        "id": 3,
        "domain": "Địa lý / Biển sâu",
        "sentence": "Áp suất kinh hoàng dưới đáy biển sâu nghiền nát thân tàu ngầm."
    },
    {
        "id": 4,
        "domain": "Truyền thông",
        "sentence": "Máy in báo liên tục xổ ra hàng ngàn trang tin tức mới."
    },
    {
        "id": 5,
        "domain": "Địa chất",
        "sentence": "Núi lửa bất ngờ phun trào dòng nham thạch đỏ rực lên bầu trời."
    },
    {
        "id": 6,
        "domain": "Khoa học",
        "sentence": "Kính hiển vi quang học soi chiếu từng chi tiết nhỏ của mẫu vật."
    },
    {
        "id": 7,
        "domain": "Lịch sử",
        "sentence": "Những người thợ cổ đại tỉ mỉ quấn băng lanh ướp xác vị vua."
    },
    {
        "id": 8,
        "domain": "Hải dương",
        "sentence": "Con tàu thám hiểm lặn sâu xuống rãnh Mariana tối tăm."
    },
    {
        "id": 9,
        "domain": "Vũ trụ / Vật lý",
        "sentence": "Tia bức xạ mặt trời chiếu rọi và thiêu đốt bề mặt sa mạc."
    },
    {
        "id": 10,
        "domain": "Lịch sử",
        "sentence": "Đoàn quân viễn chinh rầm rộ hành quân qua sa mạc mênh mông."
    },
    {
        "id": 11,
        "domain": "Vũ trụ",
        "sentence": "Trái Đất kiên trì quay quanh Mặt Trời theo quỹ đạo elip."
    },
    {
        "id": 12,
        "domain": "Hóa sinh",
        "sentence": "Chất độc ngấm vào làm phân hủy các mô liên kết."
    },
    {
        "id": 13,
        "domain": "Khảo cổ",
        "sentence": "Họ cẩn thận đặt di hài vào quan tài bằng đá thạch."
    },
    {
        "id": 14,
        "domain": "Địa lý",
        "sentence": "Bão biển cuộn sóng dữ dội xô mạnh vào vách đá."
    },
    {
        "id": 15,
        "domain": "Sinh học",
        "sentence": "Tế bào mẹ nhanh chóng phân bào để tạo ra thế hệ mới."
    },
    {
        "id": 16,
        "domain": "Đời thường",
        "sentence": "Lưỡi dao sắc bén chém đứt sợi dây thừng."
    },
    {
        "id": 17,
        "domain": "Cơ khí",
        "sentence": "Bàn tay vặn chặt chiếc van cơ khí."
    },
    {
        "id": 18,
        "domain": "Ẩn dụ tự nhiên",
        "sentence": "Ánh chớp lóe sáng xé toạc màn đêm u tối."
    },
    {
        "id": 19,
        "domain": "Lịch sử ẩn dụ",
        "sentence": "Đế chế hùng mạnh hoàn toàn sụp đổ sau cuộc nội chiến."
    },
    {
        "id": 20,
        "domain": "Khoa học",
        "sentence": "Đồng hồ đo đạc chính xác áp suất trong buồng kín."
    }
]

async def run_tests():
    print("=" * 115)
    print("🚀 [TEST PHASE 2] BỘ KIỂM THỬ SEMANTIC MATCHER TRÊN 20 CÂU THOẠI THỰC TẾ")
    print("=" * 115)

    matcher = VerbSemanticMatcher()
    success_count = 0

    header = f"{'STT':<4} | {'Lĩnh vực':<16} | {'Động từ nhận diện':<18} | {'Nhóm động học':<23} | {'Motion Type':<22} | {'Trạng thái'}"
    print(header)
    print("-" * 115)

    for item in TEST_SENTENCES:
        s_id = item["id"]
        domain = item["domain"]
        sent = item["sentence"]

        entry = await matcher.match_sentence(sent, context=domain)

        if entry and "verb_vi" in entry and "category" in entry and "motion_type" in entry:
            v_vi = entry["verb_vi"]
            cat = entry["category"]
            m_type = entry["motion_type"]
            status = "✅ PASS"
            success_count += 1
        else:
            v_vi = "None"
            cat = "None"
            m_type = "None"
            status = "❌ FAIL"

        print(f"{s_id:<4} | {domain:<16} | {v_vi:<18} | {cat:<23} | {m_type:<22} | {status}")

    print("-" * 115)
    print(f"📊 KẾT QUẢ TỔNG KẾT: {success_count}/{len(TEST_SENTENCES)} câu nhận diện thành công ({success_count/len(TEST_SENTENCES)*100:.1f}%)")
    print("=" * 115)

    assert success_count == len(TEST_SENTENCES), f"❌ Tỷ lệ thành công chỉ đạt {success_count}/{len(TEST_SENTENCES)}, yêu cầu 100%!"

    # Kiểm tra thử nghiệm enrich_scene_layout
    print("\n🔬 [TEST ENRICHMENT] Kiểm tra khả năng làm giàu Scene Layout...")
    sample_layout = {
        "archetype": "industrial_social",
        "color_field": "Charcoal Kraft",
        "hero_element": {"name": "hydraulic press", "position": [0.5, 0.42]},
        "secondary_element": {"name": "metal bar", "position": [0.5, 0.68]}
    }
    enriched = matcher.enrich_scene_layout(sample_layout, TEST_SENTENCES[0]["sentence"])
    assert "timeline" in enriched, "Thiếu trường 'timeline' sau khi enrich!"
    assert len(enriched["timeline"]) >= 2, "Timeline cần ít nhất 2 action (hero & target)!"
    print(f"✅ Scene layout đã được đắp timeline tự động: {len(enriched['timeline'])} actions!")
    for act in enriched["timeline"]:
        print(f"   * Target='{act['target']}', Action='{act['action']}', Time={act.get('time_range', act.get('spawn_time'))}")

    print("\n🎉 PHASE 2 SEMANTIC MATCHER TEST: HOÀN TẤT VÀ ĐẠT CHUẨN 100%!")

if __name__ == "__main__":
    asyncio.run(run_tests())
