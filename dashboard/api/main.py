import os
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger
from dashboard.api.database import create_tables
from dashboard.api.routes import jobs, channels
from dashboard.api.security import ApiKeyMiddleware, is_auth_enabled
from dashboard.api.upload_validation import validate_audio_upload

# Ensure static and asset directories exist before mounting
os.makedirs("./data", exist_ok=True)
os.makedirs("./assets", exist_ok=True)
os.makedirs("./assets/voices", exist_ok=True)

app = FastAPI(
    title="AutoVideoFactory API",
    description="API backend for AutoVideoFactory Dashboard",
    version="1.0.0"
)

# Task 5.4: khoá endpoint ghi bằng X-API-Key khi đã đặt SECRET_KEY
app.add_middleware(ApiKeyMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static directories
app.mount("/files", StaticFiles(directory="data"), name="files")
app.mount("/assets", StaticFiles(directory="assets"), name="assets")

# Include API routers
app.include_router(jobs.router, prefix="/jobs", tags=["Jobs"])
app.include_router(channels.router, prefix="/channels", tags=["Channels"])

@app.on_event("startup")
async def startup_event():
    logger.info("Starting up AutoVideoFactory API")
    if is_auth_enabled():
        logger.info("🔒 [API Security] X-API-Key đang BẬT cho các endpoint ghi (SECRET_KEY đã đặt).")
    else:
        logger.warning(
            "⚠️ [API Security] SECRET_KEY chưa đặt — endpoint ghi KHÔNG khoá (chỉ nên dùng khi dev localhost)."
        )
    create_tables()
    try:
        from dashboard.api.publish_scheduler import start_publish_scheduler

        app.state.publish_scheduler = start_publish_scheduler()
    except Exception as exc:
        logger.warning(f"Publish scheduler startup skipped: {exc}")
        app.state.publish_scheduler = None
    logger.info("Database tables initialized")

@app.on_event("shutdown")
async def shutdown_event():
    try:
        from dashboard.api.publish_scheduler import shutdown_publish_scheduler

        shutdown_publish_scheduler()
    except Exception as exc:
        logger.warning(f"Publish scheduler shutdown skipped: {exc}")

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/voices")
def get_voices():
    # 1. Built-in VieNeu 25 Preset Voices
    preset_voices = [
        "default",
        "default (Minh Quân - Chuẩn)",
        "⭐ Thiện Minh — Nam · Bắc · Kể chuyện",
        "⭐ Trúc Ly — Nữ · Bắc · Tự nhiên",
        "⭐ Mai Anh — Nữ · Bắc · Tin tức",
        "⭐ Hải Đăng — Nam · Bắc · Tự nhiên",
        "⭐ Thùy Dung — Nữ · Nam · Tin tức",
        "⭐ Thái Sơn — Nam · Nam · Kể chuyện",
        "⭐ Thiền Tâm Đức — Nam · Bắc · Kể chuyện",
        "⭐ Ngọc Huyền — Nữ · Bắc · Tự nhiên",
        "⭐ Quang Sơn — Nam · Trung · Tự nhiên",
        "⭐ Ngọc Trân — Nữ · Trung · Tự nhiên",
        "Minh Đức — Nam · Bắc · Tin tức",
        "Phạm Tuyên — Nam · Bắc · Tự nhiên",
        "Xuân Vĩnh — Nam · Bắc · Tự nhiên",
        "Thanh Bình — Nam · Bắc · Kể chuyện",
        "Ngọc Linh — Nữ · Bắc · Kể chuyện",
        "Đoan Trang — Nữ · Bắc · Tự nhiên",
        "Thục Đoan — Nữ · Nam · Kể chuyện",
        "Minh Triết — Nam · Nam · Tin tức",
        "Mỹ Duyên — Nữ · Nam · Đọc truyện",
        "Quỳnh Anh — Nữ · Bắc · Đọc truyện",
        "Đức Trí — Nam · Nam · Đọc truyện",
        "Kim Thanh — Nữ · Nam · Đọc truyện",
        "Quốc Tuấn — Nam · Bắc · Tự nhiên"
    ]
    
    # 2. Uploaded Custom Voice Samples in assets/voices/
    voices_dir = "./assets/voices"
    os.makedirs(voices_dir, exist_ok=True)
    custom_files = [f for f in os.listdir(voices_dir) if f.lower().endswith((".wav", ".mp3"))]
    custom_voices = [f for f in sorted(custom_files)]
    
    return {"voices": custom_voices + preset_voices}

@app.post("/voices/upload")
async def upload_voice(file: UploadFile = File(...)):
    filename = os.path.basename(file.filename or "")
    if not filename:
        raise HTTPException(status_code=400, detail="Filename cannot be empty")
    ext = os.path.splitext(filename)[1].lower()
    if ext not in [".wav", ".mp3"]:
        raise HTTPException(status_code=400, detail="Only .wav and .mp3 files are supported")

    # Task 5.4: validate dung lượng + magic bytes qua helper dùng chung
    # (file .exe đổi đuôi .mp3 bị chặn tại đây)
    content, _fmt = await validate_audio_upload(file)

    voices_dir = "./assets/voices"
    os.makedirs(voices_dir, exist_ok=True)
    save_path = os.path.join(voices_dir, filename)

    with open(save_path, "wb") as f:
        f.write(content)

    return {
        "status": "success",
        "filename": filename,
        "path": f"assets/voices/{filename}"
    }

@app.get("/voices/preview")
async def preview_voice(voice: str = "default"):
    """Synthesize or serve cached voice preview audio for the requested voice."""
    clean_voice = voice
    if " — " in clean_voice:
        clean_voice = clean_voice.split(" — ")[0].replace("⭐ ", "").strip()
    elif "📁 [Tự tải lên] " in clean_voice:
        clean_voice = clean_voice.replace("📁 [Tự tải lên] ", "").strip()
    elif "default" in clean_voice.lower():
        clean_voice = "Minh Quân"
        
    cache_dir = Path("data/cache/voice_previews")
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    custom_voice_path = Path("assets/voices") / clean_voice
    safe_name = "".join([c if c.isalnum() else "_" for c in clean_voice])
    out_file = cache_dir / f"preview_{safe_name}.wav"
    
    if not out_file.exists():
        from core.tts_engine.vieneu_client import VieNeuClient
        client = VieNeuClient()
        demo_text = f"Xin chào, đây là giọng đọc mẫu {clean_voice} trên hệ thống Auto Video Factory."
        if custom_voice_path.exists():
            await client.synthesize(demo_text, output_path=str(out_file), ref_audio=str(custom_voice_path))
        else:
            await client.synthesize(demo_text, output_path=str(out_file), voice=clean_voice)
            
    return FileResponse(str(out_file), media_type="audio/wav")

@app.get("/")
def read_root():
    return {
        "name": "AutoVideoFactory API",
        "docs": "/docs",
        "status": "running"
    }
