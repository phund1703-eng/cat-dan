"""
AutoVideoFactory — Tool hướng dẫn và thực hiện Clone Giọng Nói
Hỗ trợ tạo mẫu âm thanh và đăng ký reference_id trên Fish Audio API / Local
"""

import os
import sys
import asyncio
from pathlib import Path
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

from core.tts_engine.fish_audio_client import FishAudioClient


async def clone_my_voice():
    print("=" * 60)
    print("🎙️  HƯỚNG DẪN CLONE GIỌNG NÓI CÁ NHÂN (FISH AUDIO / XTTS)")
    print("=" * 60)
    print("""
Để clone giọng nói của bạn đạt chất lượng tốt nhất:
1. Chuẩn bị 1 file âm thanh (định dạng .wav hoặc .mp3) dài từ 10 - 30 giây.
2. Giọng đọc to, rõ ràng, không có tiếng ồn môi trường, nhạc nền hoặc vang vọng.
3. Đọc một đoạn văn tự nhiên (tiếng Việt hoặc tiếng Anh).
4. Đặt file vào thư mục: assets/voices/
    Ví dụ: assets/voices/my_voice_vi.wav
    """)

    voice_dir = Path("assets/voices")
    voice_dir.mkdir(parents=True, exist_ok=True)

    files = list(voice_dir.glob("*.wav")) + list(voice_dir.glob("*.mp3"))

    if not files:
        print(f"❌ Chưa tìm thấy file âm thanh nào trong: {voice_dir.resolve()}")
        print("👉 Vui lòng ghi âm và lưu vào thư mục trên, sau đó chạy lại script này.")
        return

    print("Các file âm thanh tìm thấy:")
    for idx, f in enumerate(files, 1):
        print(f"  [{idx}] {f.name} ({round(f.stat().st_size / 1024, 1)} KB)")

    choice = input("\nChọn số thứ tự file bạn muốn dùng để clone: ").strip()
    try:
        selected_file = files[int(choice) - 1]
    except (ValueError, IndexError):
        print("❌ Lựa chọn không hợp lệ.")
        return

    voice_name = input("Đặt tên đại diện cho giọng nói này (vd: giong_doc_chinh): ").strip()
    if not voice_name:
        voice_name = "my_custom_voice"

    language = input("Ngôn ngữ mẫu giọng (vi/en) [Mặc định: vi]: ").strip().lower() or "vi"

    api_key = os.getenv("FISH_AUDIO_API_KEY")
    if not api_key or api_key == "your_fish_audio_key_here":
        print("\n⚠️  Chưa cấu hình FISH_AUDIO_API_KEY trong file .env!")
        print("File mẫu của bạn sẽ được lưu cục bộ tại assets/voices/ để dùng cho local engine (XTTS).")
        print(f"✅ Đường dẫn mẫu: {selected_file.resolve()}")
        return

    print(f"\n🚀 Đang tải file '{selected_file.name}' lên Fish Audio để tạo Voice Clone...")
    client = FishAudioClient()

    try:
        ref_id = await client.clone_voice(
            audio_file_path=str(selected_file),
            name=voice_name,
            description=f"AutoVideoFactory voice clone ({language})"
        )
        print("\n" + "=" * 60)
        print("🎉 CLONE GIỌNG THÀNH CÔNG!")
        print(f"Reference ID của bạn: {ref_id}")
        print("=" * 60)
        print("\n👉 Hãy mở file .env và cập nhật dòng tương ứng:")
        if language == "vi":
            print(f"FISH_AUDIO_VI_REFERENCE_ID={ref_id}")
        else:
            print(f"FISH_AUDIO_EN_REFERENCE_ID={ref_id}")
        print("=" * 60)
    except Exception as e:
        logger.error(f"Lỗi khi clone voice: {e}")
        print("❌ Không thể clone voice qua API. Vui lòng kiểm tra lại API Key hoặc đường truyền.")


if __name__ == "__main__":
    asyncio.run(clone_my_voice())
