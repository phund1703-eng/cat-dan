import os
import json
from datetime import datetime
from typing import List, Optional
from sqlalchemy import create_engine, Column, String, DateTime, Enum as SQLEnum, Text, text
from sqlalchemy.orm import declarative_base, sessionmaker
from dashboard.api.models import JobStatus

DATABASE_URL = "sqlite:///./data/autovideofactory.db"

# Ensure data directory exists
os.makedirs("./data", exist_ok=True)

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False, "timeout": 30})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class VideoJob(Base):
    __tablename__ = "video_jobs"

    id = Column(String, primary_key=True, index=True)
    topic = Column(String, index=True)
    style = Column(String)
    language = Column(String)
    status = Column(SQLEnum(JobStatus), default=JobStatus.pending)
    stage = Column(String, default="pending")
    mode = Column(String, default="auto")
    art_style = Column(String, default="photorealistic")
    voice_preset = Column(String, default="default")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    output_path = Column(String, nullable=True)
    error = Column(String, nullable=True)
    script_data = Column(Text, nullable=True)  # JSON string
    metadata_data = Column(Text, nullable=True)  # JSON string
    pipeline_data_json = Column(Text, nullable=True)  # JSON string
    
    @property
    def script(self):
        if self.script_data:
            if isinstance(self.script_data, dict):
                return self.script_data
            try:
                return json.loads(self.script_data)
            except Exception:
                return None
        return None
        
    @script.setter
    def script(self, value):
        if isinstance(value, str):
            self.script_data = value
        else:
            self.script_data = json.dumps(value) if value is not None else None

    @property
    def extra_metadata(self):
        if self.metadata_data:
            if isinstance(self.metadata_data, dict):
                return self.metadata_data
            try:
                return json.loads(self.metadata_data)
            except Exception:
                return None
        return None

    @extra_metadata.setter
    def extra_metadata(self, value):
        if isinstance(value, str):
            self.metadata_data = value
        else:
            self.metadata_data = json.dumps(value) if value is not None else None

    @property
    def pipeline_data(self) -> Optional[dict]:
        if self.pipeline_data_json:
            if isinstance(self.pipeline_data_json, dict):
                return self.pipeline_data_json
            try:
                return json.loads(self.pipeline_data_json)
            except Exception:
                return None
        return None

    @pipeline_data.setter
    def pipeline_data(self, value):
        if isinstance(value, str):
            self.pipeline_data_json = value
        else:
            self.pipeline_data_json = json.dumps(value) if value is not None else None

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    Base.metadata.create_all(bind=engine)
    # SQLite column auto-migration to avoid OperationalError on existing databases
    try:
        with engine.begin() as conn:
            cursor = conn.execute(text("PRAGMA table_info(video_jobs)"))
            rows = cursor.fetchall()
            existing_cols = set()
            for row in rows:
                if hasattr(row, "name"):
                    existing_cols.add(row.name)
                elif hasattr(row, "__getitem__"):
                    existing_cols.add(row[1])

            migrations = [
                ("stage", "VARCHAR DEFAULT 'pending'"),
                ("mode", "VARCHAR DEFAULT 'auto'"),
                ("art_style", "VARCHAR DEFAULT 'photorealistic'"),
                ("voice_preset", "VARCHAR DEFAULT 'default'"),
                ("pipeline_data_json", "TEXT"),
            ]
            for col_name, col_type in migrations:
                if col_name not in existing_cols:
                    conn.execute(text(f"ALTER TABLE video_jobs ADD COLUMN {col_name} {col_type}"))
    except Exception:
        # Fallback in case of in-memory or alternative db engine
        pass

def create_job(
    db,
    job_id: str,
    topic: str,
    style: str,
    language: str,
    mode: str = "auto",
    art_style: str = "photorealistic",
    voice_preset: str = "default",
    stage: str = "pending"
) -> VideoJob:
    db_job = VideoJob(
        id=job_id,
        topic=topic,
        style=style,
        language=language,
        mode=mode,
        art_style=art_style,
        voice_preset=voice_preset,
        stage=stage,
        status=JobStatus.pending
    )
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job

def get_job(db, job_id: str) -> Optional[VideoJob]:
    return db.query(VideoJob).filter(VideoJob.id == job_id).first()

def list_jobs(db, status: Optional[str] = None, style: Optional[str] = None, language: Optional[str] = None):
    query = db.query(VideoJob)
    if status:
        query = query.filter(VideoJob.status == status)
    if style:
        query = query.filter(VideoJob.style == style)
    if language:
        query = query.filter(VideoJob.language == language)
    return query.all()

def update_job_status(db, job_id: str, status: JobStatus, error: Optional[str] = None) -> Optional[VideoJob]:
    job = get_job(db, job_id)
    if job:
        if isinstance(status, str):
            try:
                job.status = JobStatus(status)
            except ValueError:
                job.status = status
        else:
            job.status = status
        if error:
            job.error = error
        job.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(job)
    return job

def update_job_stage(
    db,
    job_id: str,
    stage: str,
    status: Optional[JobStatus] = None,
    pipeline_data: Optional[dict] = None,
    error: Optional[str] = None
) -> Optional[VideoJob]:
    job = get_job(db, job_id)
    if job:
        job.stage = stage
        if status is not None:
            if isinstance(status, str):
                try:
                    job.status = JobStatus(status)
                except ValueError:
                    job.status = status
            else:
                job.status = status
        if pipeline_data is not None:
            job.pipeline_data = pipeline_data
        if error is not None:
            job.error = error
        job.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(job)
    return job

def update_scene_image(
    db,
    job_id: str,
    scene_index: int,
    new_image_path: str,
    vision_gate_score: Optional[float] = None,
    vision_gate_reasoning: Optional[str] = None
) -> Optional[VideoJob]:
    job = get_job(db, job_id)
    if not job:
        return None
        
    p_data = job.pipeline_data or {}
    storyboard = p_data.setdefault("storyboard", [])
    
    # Task 5.3: ảnh do người dùng tải lên luôn mang provenance user_upload
    _upload_meta = None
    try:
        from core.media_engine.asset_provenance import build_asset_meta, read_asset_meta

        _upload_meta = read_asset_meta(new_image_path) or build_asset_meta(
            source="user_upload",
            license="User-provided upload (rights belong to the uploader)",
        )
    except Exception:
        _upload_meta = None

    found = False
    for scene in storyboard:
        if scene.get("scene_index") == scene_index:
            scene["image_path"] = new_image_path
            scene["tier_used"] = "user_uploaded"
            if _upload_meta:
                scene["asset_meta"] = _upload_meta
            if vision_gate_score is not None:
                scene["vision_gate_score"] = vision_gate_score
            if vision_gate_reasoning is not None:
                scene["vision_gate_reasoning"] = vision_gate_reasoning
            found = True
            break
            
    if not found:
        storyboard.append({
            "scene_index": scene_index,
            "image_path": new_image_path,
            "tier_used": "user_uploaded",
            "asset_meta": _upload_meta,
            "vision_gate_score": vision_gate_score if vision_gate_score is not None else 1.0,
            "vision_gate_reasoning": vision_gate_reasoning or "User uploaded image"
        })
        
    # Also update script.scenes if present
    if "script" in p_data and isinstance(p_data["script"], dict):
        scenes = p_data["script"].get("scenes", [])
        if isinstance(scenes, list):
            for sc in scenes:
                if isinstance(sc, dict) and sc.get("index") == scene_index:
                    sc["image_path"] = new_image_path
                    
    job.pipeline_data = p_data
    job.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(job)
    return job

def update_job_output(db, job_id: str, output_path: str = None, script: dict = None, meta: dict = None):
    job = get_job(db, job_id)
    if job:
        if output_path:
            job.output_path = output_path
        if script:
            job.script = script
        if meta:
            job.extra_metadata = meta
        job.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(job)
    return job
