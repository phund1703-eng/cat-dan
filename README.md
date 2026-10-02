# 🎬 AutoVideoFactory

Hệ thống sản xuất video tự động từ đầu đến cuối, hỗ trợ **5 phong cách video**, **song ngữ Việt-Anh**, tích hợp AI generation và tự động đăng lên YouTube/TikTok/Facebook.

## ✨ Tính Năng

| Tính năng | Mô tả |
|---|---|
| 🤖 Script AI | Gemini tự động viết kịch bản theo từng thể loại |
| 🎙️ Voice Clone | Fish Audio (VI) + Kokoro (EN) + Edge TTS (fallback) |
| 🎨 5 Phong cách | Animation 2D, Cắt dán, Whiteboard, Clip ghép, AI Avatar |
| 🌐 Song ngữ | Tạo 2 phiên bản Việt-Anh cho mỗi video |
| 📱 Multi-platform | YouTube, TikTok, Facebook/Instagram |
| 🖥️ Dashboard | Web UI quản lý job + duyệt + lịch đăng |

## 🏗️ Kiến Trúc

```
AutoVideoFactory/
├── core/                    # Engine cốt lõi
│   ├── script_engine/       # Gemini - viết kịch bản
│   ├── tts_engine/          # Fish Audio + Kokoro + Edge TTS
│   ├── media_engine/        # Pexels + Pixabay + AI images
│   └── render_engine/       # FFmpeg + MoviePy + Subtitles
├── styles/                  # 5 phong cách video
│   ├── collage_broll/       # Cắt dán / Collage
│   ├── animation_2d/        # Animation Manim
│   ├── clip_overlay/        # Clip + Text Overlay
│   ├── whiteboard/          # Whiteboard Animation
│   └── ai_avatar/           # SadTalker / MuseTalk
├── publish/                 # Đăng lên mạng xã hội
│   ├── postiz_client/       # Postiz self-hosted
│   └── platform_adapters/   # YouTube / TikTok / Facebook
├── dashboard/               # Giao diện quản lý
│   ├── api/                 # FastAPI backend
│   ├── worker/              # Celery job queue
│   └── ui/                  # Streamlit frontend
├── assets/                  # Tài nguyên
│   ├── voices/              # Mẫu giọng để clone
│   ├── avatars/             # Ảnh avatar AI
│   ├── music/               # Nhạc nền royalty-free
│   └── templates/           # Video templates
├── data/                    # Dữ liệu
│   ├── jobs/                # Metadata job
│   ├── output/              # Video đã render
│   └── cache/               # Cache assets
└── config/                  # Cấu hình
    ├── settings.yaml        # API keys + settings
    └── channels.yaml        # Cấu hình kênh
```

## 🚀 Cài Đặt Nhanh (Windows)

### Bước 1: Yêu Cầu Hệ Thống
- Windows 10/11
- Python 3.10+ ([tải tại python.org](https://python.org))
- NVIDIA GPU (RTX 3060/4060 hoặc tốt hơn) + CUDA
- Git ([tải tại git-scm.com](https://git-scm.com))
- FFmpeg ([tải tại ffmpeg.org](https://ffmpeg.org))

### Bước 2: Cài Đặt Tự Động
```bash
# Clone repo này
git clone <repo-url>
cd AutoVideoFactory

# Chạy script cài đặt
install.bat
```

### Bước 3: Cấu Hình API Keys
```bash
# Copy file env mẫu
copy .env.example .env

# Mở .env và điền API keys:
# - GEMINI_API_KEY (lấy tại aistudio.google.com)
# - FISH_AUDIO_API_KEY (lấy tại fish.audio)
# - PEXELS_API_KEY (lấy tại pexels.com/api)
# - PIXABAY_API_KEY (lấy tại pixabay.com/api)
```

### Bước 4: Khởi Động Dashboard
```bash
start.bat
```

Mở trình duyệt tại: **http://localhost:8501**

## 📖 Hướng Dẫn Sử Dụng

### Tạo Video Đầu Tiên
1. Mở Dashboard tại http://localhost:8501
2. Chọn **"Tạo Video Mới"**
3. Nhập chủ đề (ví dụ: "5 mẹo học tiếng Anh hiệu quả")
4. Chọn phong cách (Cắt dán, Animation, etc.)
5. Chọn ngôn ngữ (Tiếng Việt / Tiếng Anh / Cả hai)
6. Nhấn **"Tạo Video"** và chờ
7. Xem preview → Duyệt → Đặt lịch đăng

### Clone Giọng Của Bạn
1. Thu âm 30 giây giọng nói rõ ràng, không tiếng ồn
2. Lưu file vào `assets/voices/my_voice_vi.wav` (tiếng Việt)
3. Lưu file vào `assets/voices/my_voice_en.wav` (tiếng Anh)
4. Chạy: `python scripts/clone_voice.py`
5. Giọng của bạn sẽ được dùng cho tất cả video

## 🔧 Cấu Hình Nâng Cao

Xem file [`config/settings.yaml`](config/settings.yaml) để tùy chỉnh:
- Model LLM
- TTS engine ưu tiên
- Chất lượng video (720p/1080p)
- Nhạc nền mặc định
- Style prompt templates

## 📊 Phong Cách Video

| Phong cách | Thời gian render | GPU cần | Phù hợp |
|---|---|---|---|
| 🎞️ Cắt dán Collage | ~2 phút | Không | Tin tức, Trending |
| 🎨 Animation 2D | ~5 phút | Không | Giáo dục |
| 📹 Clip + Text | ~3 phút | Không | Marketing |
| ✏️ Whiteboard | ~5 phút | Không | Học thuật |
| 🤖 AI Avatar | ~10 phút | ~4GB VRAM | Marketing, Branding |

## 📱 Nền Tảng Hỗ Trợ

- **YouTube**: Video dài (16:9) + Shorts (9:16)
- **TikTok**: Video dọc (9:16) — draft mode
- **Facebook/Instagram**: Reels (9:16) + Posts

## 💰 Chi Phí

### Miễn Phí Hoàn Toàn:
- Gemini API: 1,500 request/ngày miễn phí
- Pexels + Pixabay: Miễn phí
- Edge TTS: Miễn phí
- Kokoro TTS: Local, miễn phí (Apache 2.0)

### Nâng Cấp Tuỳ Chọn (<20$/tháng):
- Fish Audio Pro: ~5$/tháng (voice clone chất lượng cao)
- Gemini Pro: ~5-10$/tháng (nếu vượt free tier)

## 🤝 Đóng Góp

Xem [CONTRIBUTING.md](CONTRIBUTING.md) để biết cách đóng góp.

## 📄 Giấy Phép

MIT License — Xem [LICENSE](LICENSE)
