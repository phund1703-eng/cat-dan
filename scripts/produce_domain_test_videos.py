"""
AutoVideoFactory — Produce 3 Domain-Specific Collage B-Roll Videos
Sản xuất 3 video ngắn (Shorts 9:16, 1080x1920) theo tiêu chuẩn nâng cấp toàn diện:
1. Video 1: Sinh học (biology) - "Hành trình tế bào bạch cầu tiêu diệt vi khuẩn" -> output/video_biology.mp4
2. Video 2: Địa lý (geography) - "Bí mật rãnh Mariana - Vực sâu tăm tối nhất hành tinh" -> output/video_geography.mp4
3. Video 3: Lịch sử (history) - "Bí mật kỹ thuật ướp xác của các Pharaoh Ai Cập" -> output/video_history.mp4
"""

import os
import sys
import asyncio
import subprocess
from pathlib import Path
from loguru import logger

ROOT_DIR = Path(__file__).parent.parent.resolve()
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from styles.collage_broll.collage_engine import CollageEngine
from core.tts_engine.tts_manager import TTSManager


DOMAIN_VIDEOS = [
    {
        "id": "video_biology",
        "topic": "Hành trình tế bào bạch cầu tiêu diệt vi khuẩn",
        "title": "Cuộc Chiến Vô Hình Của Tế Bào Bạch Cầu",
        "description": "Hành trình nghẹt thở của các tế bào bạch cầu truy lùng và tiêu diệt vi khuẩn gây bệnh.",
        "topic_domain": "biology",
        "hashtags": ["#sinhhoc", "#bachcau", "#khoahoc", "#shorts"],
        "scenes": [
            {
                "narration": "Mỗi giây trôi qua, cơ thể chúng ta là một bãi chiến trường khốc liệt chống lại hàng triệu vi khuẩn xâm nhập.",
                "focal_keyword": "bacterium",
                "secondary_keyword": "microscope",
                "layout_type": "hero_center",
                "topic_domain": "biology",
                "has_hand": False,
                "has_camera": False,
                "color_field": "Deep Cobalt",
                "color_hex": "1D3557",
                "assembly_order": "thị trường kính hiển vi -> vi khuẩn gai nhọn trung tâm -> kính hiển vi góc",
                "duration": 5.0
            },
            {
                "narration": "Ngay khi phát hiện mầm bệnh, các tế bào bạch cầu đại thực bào lập tức vươn xúc tu bao vây kẻ thù.",
                "focal_keyword": "white blood cell",
                "secondary_keyword": "bacterium",
                "layout_type": "split_contrast",
                "topic_domain": "biology",
                "has_hand": False,
                "has_camera": False,
                "color_field": "Mustard Cardstock",
                "color_hex": "E9C46A",
                "assembly_order": "thước đo micromet -> bạch cầu bên trái -> vi khuẩn bên phải -> ánh sáng spotlight",
                "duration": 5.0
            },
            {
                "narration": "Quá trình thực bào diễn ra chớp nhoáng, nuốt chửng và phân giải hoàn toàn vi khuẩn để bảo vệ sự sống.",
                "focal_keyword": "white blood cell",
                "secondary_keyword": "dna",
                "layout_type": "stage_prop",
                "topic_domain": "biology",
                "has_hand": False,
                "has_camera": False,
                "color_field": "Teal & Coral",
                "color_hex": "2A9D8F",
                "assembly_order": "đĩa petri elip -> đèn rọi trung tâm -> bạch cầu tiêu diệt mầm bệnh -> chuỗi xoắn dna",
                "duration": 5.0
            }
        ]
    },
    {
        "id": "video_geography",
        "topic": "Bí mật rãnh Mariana - Vực sâu tăm tối nhất hành tinh",
        "title": "Bí Mật Rãnh Mariana - Vực Sâu Tăm Tối Nhất Hành Tinh",
        "description": "Khám phá rãnh Mariana nơi đáy đại dương với áp suất khổng lồ và sinh vật kỳ bí.",
        "topic_domain": "geography",
        "hashtags": ["#dialy", "#ranhmariana", "#daiduong", "#shorts"],
        "scenes": [
            {
                "narration": "Rãnh Mariana sâu gần mười một nghìn mét, nơi bóng tối vĩnh cửu bao trùm đáy đại dương.",
                "focal_keyword": "pressure gauge",
                "secondary_keyword": "compass",
                "layout_type": "hero_center",
                "topic_domain": "geography",
                "has_hand": False,
                "has_camera": False,
                "color_field": "Charcoal Kraft",
                "color_hex": "264653",
                "assembly_order": "lưới hải đồ kinh vĩ -> đồng hồ đo áp suất đáy biển -> hoa tiêu la bàn",
                "duration": 5.0
            },
            {
                "narration": "Áp suất nơi đây gấp hơn một nghìn lần mặt biển, đủ sức nghiền nát mọi tàu ngầm thông thường.",
                "focal_keyword": "submarine",
                "secondary_keyword": "anchor",
                "layout_type": "stage_prop",
                "topic_domain": "geography",
                "has_hand": False,
                "has_camera": False,
                "color_field": "Deep Cobalt",
                "color_hex": "1D3557",
                "assembly_order": "thềm đá trầm tích đáy biển -> đèn rọi tàu lặn -> tàu ngầm thám hiểm -> mỏ neo sắt",
                "duration": 5.0
            },
            {
                "narration": "Dù vậy, các sinh vật kỳ dị phát quang vẫn phát triển mạnh mẽ, mở ra cánh cửa tiến hóa chưa từng biết.",
                "focal_keyword": "anglerfish",
                "secondary_keyword": "compass",
                "layout_type": "surreal_interaction",
                "topic_domain": "geography",
                "has_hand": False,
                "has_camera": True,
                "color_field": "Plum & Gold",
                "color_hex": "4A235A",
                "assembly_order": "đường đẳng sâu bathymetric -> chùm sáng rọi -> cá lồng đèn phát quang -> máy quay quan sát",
                "duration": 5.0
            }
        ]
    },
    {
        "id": "video_history",
        "topic": "Bí mật kỹ thuật ướp xác của các Pharaoh Ai Cập",
        "title": "Bí Mật Kỹ Thuật Ướp Xác Của Các Pharaoh Ai Cập",
        "description": "Nghệ thuật ướp xác đỉnh cao hàng nghìn năm trước của nền văn minh Ai Cập cổ đại.",
        "topic_domain": "history",
        "hashtags": ["#lichsu", "#aocap", "#pharaoh", "#shorts"],
        "scenes": [
            {
                "narration": "Người Ai Cập cổ đại tin rằng thể xác phải nguyên vẹn thì linh hồn mới có thể bước vào cõi vĩnh hằng.",
                "focal_keyword": "pharaoh",
                "secondary_keyword": "pyramid",
                "layout_type": "hero_center",
                "topic_domain": "history",
                "has_hand": False,
                "has_camera": False,
                "color_field": "Burnt Terracotta",
                "color_hex": "D44D22",
                "assembly_order": "khung văn thư hoàng gia -> mặt nạ vàng pharaoh trung tâm -> kim tự tháp góc",
                "duration": 5.0
            },
            {
                "narration": "Họ tỉ mỉ loại bỏ nội tạng và bảo quản riêng biệt trong bốn chiếc bình canopic bằng đá alabaster.",
                "focal_keyword": "canopic jar",
                "secondary_keyword": "papyrus",
                "layout_type": "split_contrast",
                "topic_domain": "history",
                "has_hand": True,
                "has_camera": False,
                "color_field": "Mustard Cardstock",
                "color_hex": "E9C46A",
                "assembly_order": "đường phân ranh cổ -> bình canopic bên trái -> cuộn giấy papyrus bên phải -> bàn tay chỉ dẫn cổ điển",
                "duration": 5.0
            },
            {
                "narration": "Sau bảy mươi ngày ướp muối natron và bọc vải lanh, thi hài được an táng trong cỗ quan tài vàng lộng lẫy.",
                "focal_keyword": "sarcophagus",
                "secondary_keyword": "ankh",
                "layout_type": "stage_prop",
                "topic_domain": "history",
                "has_hand": False,
                "has_camera": False,
                "color_field": "Plum & Gold",
                "color_hex": "4A235A",
                "assembly_order": "bệ đá sa thạch phối cảnh -> ánh sáng vàng rọi -> cỗ quan tài vàng sarcophagus -> biểu tượng ankh",
                "duration": 5.0
            }
        ]
    }
]


async def produce_all():
    output_dir = Path("output").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    temp_tts_dir = Path("data/temp_tts").resolve()
    temp_tts_dir.mkdir(parents=True, exist_ok=True)

    tts_manager = TTSManager()
    engine = CollageEngine()

    results = []

    for idx, conf in enumerate(DOMAIN_VIDEOS, start=1):
        vid_id = conf["id"]
        logger.info(f"\n=======================================================")
        logger.info(f"🚀 BẮT ĐẦU SẢN XUẤT VIDEO DOMAIN {idx}/3: [{vid_id}] - {conf['title']}")
        logger.info(f"=======================================================")

        # 1. Sinh TTS EdgeTTS chuẩn tiếng Việt
        audio_dir = temp_tts_dir / vid_id
        audio_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"🎙️ Sinh TTS EdgeTTS cho 3 cảnh...")
        audio_files = await tts_manager.synthesize_scenes(
            scenes=conf["scenes"],
            language="vi",
            output_dir=str(audio_dir)
        )
        logger.info(f"✅ Đã tạo {len(audio_files)} files audio: {audio_files}")

        # 2. Xuất video bằng CollageEngine
        out_video_path = output_dir / f"{vid_id}.mp4"
        script_dict = {
            "title": conf["title"],
            "description": conf["description"],
            "topic_domain": conf["topic_domain"],
            "hashtags": conf["hashtags"],
            "scenes": conf["scenes"]
        }

        final_path = await engine.create_video(
            script=script_dict,
            language="vi",
            output_path=str(out_video_path),
            format="shorts",
            audio_files=audio_files,
            media_files=[]
        )

        logger.success(f"🎉 Hoàn thành video {idx}: {final_path}")

        # 3. Trích xuất khung hình tiêu biểu từ mỗi cảnh (Scene 1, Scene 2, Scene 3)
        f1_path = output_dir / f"{vid_id}_frame_1.jpg"
        f2_path = output_dir / f"{vid_id}_frame_2.jpg"
        f3_path = output_dir / f"{vid_id}_frame_3.jpg"

        cmd_f1 = [
            "ffmpeg", "-y", "-ss", "00:00:03.80", "-i", str(final_path),
            "-vframes", "1", "-q:v", "2", str(f1_path)
        ]
        cmd_f2 = [
            "ffmpeg", "-y", "-ss", "00:00:09.20", "-i", str(final_path),
            "-vframes", "1", "-q:v", "2", str(f2_path)
        ]
        cmd_f3 = [
            "ffmpeg", "-y", "-ss", "00:00:14.50", "-i", str(final_path),
            "-vframes", "1", "-q:v", "2", str(f3_path)
        ]
        subprocess.run(cmd_f1, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
        subprocess.run(cmd_f2, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
        subprocess.run(cmd_f3, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
        logger.info(f"📸 Đã trích xuất khung hình: {f1_path.name}, {f2_path.name}, {f3_path.name}")

        results.append({
            "id": vid_id,
            "title": conf["title"],
            "video": str(final_path),
            "frame1": str(f1_path),
            "frame2": str(f2_path),
            "frame3": str(f3_path)
        })

    logger.success(f"\n✨ TẤT CẢ 3 VIDEO THEO DOMAIN ĐÃ ĐƯỢC XUẤT XƯỞNG THÀNH CÔNG TẠI THƯ MỤC 'output/'!")
    for r in results:
        logger.info(f" - {r['id']}: {r['video']} | Frames: {r['frame1']}, {r['frame2']}, {r['frame3']}")


if __name__ == "__main__":
    asyncio.run(produce_all())
