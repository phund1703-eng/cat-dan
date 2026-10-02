"""
AutoVideoFactory — System Diagnostic & Health Check Tool
Kiểm tra từng thành phần để đảm bảo hệ thống sẵn sàng hoạt động
"""

import os
import sys
import shutil
import asyncio
from pathlib import Path
from loguru import logger
from dotenv import load_dotenv

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Đảm bảo root directory luôn nằm trong sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

load_dotenv(ROOT_DIR / ".env")


async def check_ffmpeg():
    print("1. Kiểm tra FFmpeg...")
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        print(f"   ✅ FFmpeg tìm thấy tại: {ffmpeg_path}")
        return True
    else:
        print("   ❌ Không tìm thấy FFmpeg trong PATH. Vui lòng cài đặt FFmpeg.")
        return False


async def check_gemini():
    print("\n2. Kiểm tra Gemini API (Dual-Key Support)...")
    key1 = os.getenv("GEMINI_API_KEY_1") or os.getenv("GEMINI_API_KEY")
    key2 = os.getenv("GEMINI_API_KEY_2")
    valid_keys = [k for k in [key1, key2] if k and not k.strip().startswith("your_")]
    
    if not valid_keys:
        print("   ⚠️  Chưa điền GEMINI_API_KEY_1 hoặc GEMINI_API_KEY_2 trong .env (đang là placeholder).")
        print("   👉 Hãy điền key từ https://aistudio.google.com/app/apikey vào .env để gọi trực tiếp Gemini.")
        print("   ℹ️  (Hệ thống có kịch bản mẫu chất lượng cao sẵn sàng chạy thử nghiệm offline)")
        return True
        
    try:
        from core.script_engine.gemini_client import GeminiClient
        client = GeminiClient()
        res = await client.generate("Xin chào, hãy trả lời 'OK' nếu bạn hoạt động.")
        print(f"   ✅ Kết nối Gemini thành công! Phản hồi: {res[:50].strip()}")
        return True
    except Exception as e:
        print(f"   ❌ Lỗi kết nối Gemini: {e}")
        return False


async def check_edge_tts():
    print("\n3. Kiểm tra Edge TTS (miễn phí)...")
    try:
        from core.tts_engine.edge_tts_client import EdgeTTSClient
        client = EdgeTTSClient()
        test_file = Path("data/cache/test_tts.mp3")
        test_file.parent.mkdir(parents=True, exist_ok=True)
        await client.synthesize("Xin chào, đây là bài kiểm tra giọng đọc.", "vi", str(test_file))
        if test_file.exists() and test_file.stat().st_size > 0:
            print(f"   ✅ Edge TTS hoạt động hoàn hảo! Đã tạo: {test_file}")
            test_file.unlink()
            return True
        else:
            print("   ❌ File TTS không tạo được.")
            return False
    except Exception as e:
        print(f"   ❌ Lỗi Edge TTS: {e}")
        return False


async def check_media_clients():
    print("\n4. Kiểm tra Pexels & Pixabay...")
    p_key = os.getenv("PEXELS_API_KEY")
    px_key = os.getenv("PIXABAY_API_KEY")
    if not p_key or p_key == "your_pexels_key_here":
        print("   ℹ️  PEXELS_API_KEY chưa cấu hình (dùng stock video mẫu hoặc download thủ công).")
    else:
        print("   ✅ Pexels API Key đã có.")

    if not px_key or px_key == "your_pixabay_key_here":
        print("   ℹ️  PIXABAY_API_KEY chưa cấu hình.")
    else:
        print("   ✅ Pixabay API Key đã có.")
    return True


async def run_diagnostics():
    print("=" * 60)
    print("🩺 AUTOVIDEOFACTORY — KIỂM TRA TOÀN DIỆN HỆ THỐNG")
    print("=" * 60)

    f_ok = await check_ffmpeg()
    g_ok = await check_gemini()
    t_ok = await check_edge_tts()
    m_ok = await check_media_clients()

    print("\n" + "=" * 60)
    print("KẾT QUẢ TỔNG QUAN:")
    print(f" - FFmpeg: {'✅ Sẵn sàng' if f_ok else '❌ Cần cài đặt'}")
    print(f" - Gemini LLM: {'✅ Sẵn sàng' if g_ok else '⚠️ Cần kiểm tra key'}")
    print(f" - TTS (Edge): {'✅ Sẵn sàng' if t_ok else '❌ Lỗi'}")
    print("=" * 60)

    if f_ok and t_ok:
        print("🎉 Hệ thống đã đủ điều kiện cơ bản để chạy thử tạo video!")
        print("👉 Thử chạy lệnh: python pipeline.py \"Bí quyết quản lý thời gian\" collage_broll vi shorts")
    else:
        print("⚠️ Hãy hoàn thành cài đặt các thành phần bị thiếu trước khi bắt đầu.")


if __name__ == "__main__":
    asyncio.run(run_diagnostics())
