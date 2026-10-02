"""
AutoVideoFactory — Produce 3 Random Collage B-Roll Videos
Sản xuất 3 video ngắn (Shorts 9:16, 1080x1920) theo phong cách Collage B-Roll:
1. Video 1: Vũ trụ & Hố đen (hero_center, split_contrast, surreal_interaction)
2. Video 2: Tâm lý học hành vi (stage_prop, hero_center, split_contrast)
3. Video 3: Lịch sử phát minh (surreal_interaction, stage_prop, hero_center)
"""

import os
import sys
import asyncio
import subprocess
from pathlib import Path
from loguru import logger

# Add project root to sys.path
ROOT_DIR = Path(__file__).parent.parent.resolve()
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from styles.collage_broll.collage_engine import CollageEngine
from core.tts_engine.tts_manager import TTSManager


VIDEOS_CONFIG = [
    {
        "id": "video_01_random",
        "topic": "Vũ trụ & Bí ẩn Hố đen",
        "title": "Bí Ẩn Hố Đen Và Chân Trời Sự Kiện",
        "description": "Khám phá bí ẩn hố đen và sự giãn nở thời gian nơi chân trời sự kiện.",
        "hashtags": ["#vutru", "#hồđen", "#khoahoc", "#shorts"],
        "scenes": [
            {
                "narration": "Hố đen là vùng không gian có lực hấp dẫn cực đại, nuốt chửng mọi vật chất xung quanh.",
                "focal_keyword": "black hole",
                "secondary_keyword": "hourglass",
                "layout_type": "hero_center",
                "color_field": "Deep Cobalt",
                "color_hex": "1D3557",
                "assembly_order": "khung tem cổ điển -> hố đen trung tâm -> đồng hồ cát góc phải -> máy quay cổ điển",
                "duration": 5.0
            },
            {
                "narration": "Càng tiến sát chân trời sự kiện, thời gian càng trôi chậm lại so với phần còn lại của vũ trụ.",
                "focal_keyword": "astronaut",
                "secondary_keyword": "clock",
                "layout_type": "split_contrast",
                "color_field": "Burnt Terracotta",
                "color_hex": "D44D22",
                "assembly_order": "vạch chia đối xứng -> hai luồng đèn chiếu -> phi hành gia bên trái -> đồng hồ bên phải -> bàn tay chỉ dẫn",
                "duration": 5.0
            },
            {
                "narration": "Không chỉ hủy diệt, hố đen siêu khối lượng chính là trái tim định hình nên toàn bộ thiên hà.",
                "focal_keyword": "galaxy",
                "secondary_keyword": "compass",
                "layout_type": "surreal_interaction",
                "color_field": "Plum & Gold",
                "color_hex": "4A235A",
                "assembly_order": "vòng tròn đồng tâm -> luồng sáng từ tay -> dải ngân hà -> la bàn cổ -> bàn tay khổng lồ đặt trung tâm",
                "duration": 5.0
            }
        ]
    },
    {
        "id": "video_02_random",
        "topic": "Tâm lý học hành vi: Nghịch lý lựa chọn",
        "title": "Nghịch Lý Của Sự Lựa Chọn Trong Cuộc Sống",
        "description": "Tại sao càng nhiều lựa chọn con người lại càng kém hạnh phúc?",
        "hashtags": ["#tamlyhoc", "#hanhvi", "#trietly", "#shorts"],
        "scenes": [
            {
                "narration": "Chúng ta thường lầm tưởng rằng càng có nhiều lựa chọn thì cuộc sống sẽ càng tự do và hạnh phúc.",
                "focal_keyword": "scale",
                "secondary_keyword": "brain",
                "layout_type": "stage_prop",
                "color_field": "Mustard Cardstock",
                "color_hex": "E9C46A",
                "assembly_order": "sàn cờ phối cảnh 3D -> đèn vàng rọi -> cán cân công lý -> bàn tay thao túng mép trên",
                "duration": 5.0
            },
            {
                "narration": "Nhưng quá nhiều lựa chọn sẽ khiến não bộ kiệt sức và rơi vào trạng thái tê liệt quyết định.",
                "focal_keyword": "brain",
                "secondary_keyword": "chains",
                "layout_type": "hero_center",
                "color_field": "Teal & Coral",
                "color_hex": "2A9D8F",
                "assembly_order": "hộp tem thư -> quầng sáng trung tâm -> bộ não tư duy -> sợi xích trói buộc -> máy quay cổ điển",
                "duration": 5.0
            },
            {
                "narration": "Học cách buông bỏ và hài lòng với điều đủ tốt mới chính là chìa khóa mở ra sự thanh thản.",
                "focal_keyword": "golden key",
                "secondary_keyword": "mask",
                "layout_type": "split_contrast",
                "color_field": "Charcoal Kraft",
                "color_hex": "264653",
                "assembly_order": "đường ranh giới -> chùm sáng hai bên -> chiếc chìa khóa vàng bên trái -> mặt nạ bên phải -> bàn tay vintage",
                "duration": 5.0
            }
        ]
    },
    {
        "id": "video_03_random",
        "topic": "Lịch sử phát minh: Chiếc bóng đèn điện",
        "title": "Chiếc Bóng Đèn Thắp Sáng Văn Minh Nhân Loại",
        "description": "Hành trình đưa ánh sáng nhân tạo vào đời sống và thay đổi hoàn toàn nền văn minh.",
        "hashtags": ["#lichsu", "#phatminh", "#edison", "#shorts"],
        "scenes": [
            {
                "narration": "Trước khi có đèn điện, màn đêm từng là rào cản khổng lồ giam cầm năng suất và nền văn minh.",
                "focal_keyword": "light bulb",
                "secondary_keyword": "clock",
                "layout_type": "surreal_interaction",
                "color_field": "Burnt Terracotta",
                "color_hex": "D44D22",
                "assembly_order": "vòng tròn ma trận -> chùm sáng từ trên -> chiếc bóng đèn phát quang -> đồng hồ -> bàn tay khổng lồ",
                "duration": 5.0
            },
            {
                "narration": "Hàng nghìn lần thất bại không làm nản lòng những nhà phát minh kiên trì tìm kiếm sợi đốt hoàn hảo.",
                "focal_keyword": "vintage camera",
                "secondary_keyword": "compass",
                "layout_type": "stage_prop",
                "color_field": "Deep Cobalt",
                "color_hex": "1D3557",
                "assembly_order": "bục sân khấu 3D -> đèn spotlight -> máy quay phim vintage -> la bàn định hướng -> bàn tay từ mép trên",
                "duration": 5.0
            },
            {
                "narration": "Khoảnh khắc dây tóc bừng sáng đã mở ra kỷ nguyên văn minh hai mươi bốn giờ cho toàn nhân loại.",
                "focal_keyword": "golden key",
                "secondary_keyword": "hourglass",
                "layout_type": "hero_center",
                "color_field": "Plum & Gold",
                "color_hex": "4A235A",
                "assembly_order": "tem thư cổ điển -> quầng sáng tròn -> chìa khóa vàng -> đồng hồ cát -> máy quay phim lùi góc",
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

    for idx, conf in enumerate(VIDEOS_CONFIG, start=1):
        vid_id = conf["id"]
        logger.info(f"\n=======================================================")
        logger.info(f"🚀 BẮT ĐẦU SẢN XUẤT VIDEO {idx}/3: [{vid_id}] - {conf['title']}")
        logger.info(f"=======================================================")

        # 1. Sinh TTS giọng đọc chuẩn tiếng Việt
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

        # 3. Trích xuất các khung hình tiêu biểu từ mỗi video (Scene 1, Scene 2, Scene 3)
        f1_path = output_dir / f"{vid_id}_frame_1.jpg"
        f2_path = output_dir / f"{vid_id}_frame_2.jpg"
        f3_path = output_dir / f"{vid_id}_frame_3.jpg"

        cmd_f1 = [
            "ffmpeg", "-y", "-ss", "00:00:02.50", "-i", str(final_path),
            "-vframes", "1", "-q:v", "2", str(f1_path)
        ]
        cmd_f2 = [
            "ffmpeg", "-y", "-ss", "00:00:07.50", "-i", str(final_path),
            "-vframes", "1", "-q:v", "2", str(f2_path)
        ]
        cmd_f3 = [
            "ffmpeg", "-y", "-ss", "00:00:12.00", "-i", str(final_path),
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

    logger.success(f"\n✨ TẤT CẢ 3 VIDEO ĐÃ ĐƯỢC XUẤT XƯỞNG THÀNH CÔNG TẠI THƯ MỤC 'output/'!")
    for r in results:
        logger.info(f" - {r['id']}: {r['video']} | Frames: {r['frame1']}, {r['frame2']}")


if __name__ == "__main__":
    asyncio.run(produce_all())
