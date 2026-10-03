from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class VideoStyle(str, Enum):
    collage_broll = "collage_broll"
    animation_2d = "animation_2d"
    clip_overlay = "clip_overlay"
    whiteboard = "whiteboard"
    ai_avatar = "ai_avatar"

class Language(str, Enum):
    vi = "vi"
    en = "en"
    both = "both"

class VideoFormat(str, Enum):
    shorts = "shorts"      # 9:16
    landscape = "landscape" # 16:9

class JobStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    done = "done"
    failed = "failed"
    approved = "approved"
    scheduled = "scheduled"
    published = "published"
    publish_failed = "publish_failed"
    rejected = "rejected"

class SourceRef(BaseModel):
    """One citation attached to a scene (Task 2.1 schema)."""
    title: str = ""
    url: str
    publisher: str = ""
    accessed_date: str = ""  # YYYY-MM-DD

    @field_validator("url")
    @classmethod
    def validate_source_url(cls, v: str) -> str:
        v = (v or "").strip()
        if not v.startswith(("http://", "https://")):
            raise ValueError("source url must start with http:// or https://")
        host = v.split("://", 1)[-1].split("/")[0].split(":")[0]
        if "." not in host or host in ("localhost",):
            raise ValueError("source url must contain a real domain (e.g. who.int)")
        return v


class CreateJobRequest(BaseModel):
    topic: str
    style: VideoStyle
    language: Language = Language.vi
    format: VideoFormat = VideoFormat.shorts
    quality: str = "standard"  # standard | premium
    channel_id: Optional[str] = None
    mode: str = "auto"
    art_style: str = "photorealistic"
    voice_preset: str = "default"

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        if v not in ("auto", "step_by_step"):
            raise ValueError("mode must be strictly either 'auto' or 'step_by_step'")
        return v

class JobResponse(BaseModel):
    id: str
    topic: str
    style: str
    language: str
    status: JobStatus
    stage: str = "pending"
    mode: str = "auto"
    art_style: Optional[str] = "photorealistic"
    voice_preset: Optional[str] = "default"
    created_at: datetime
    updated_at: Optional[datetime] = None
    output_path: Optional[str] = None
    error: Optional[str] = None
    script: Optional[dict] = None
    metadata: Optional[dict] = None  # title, description, hashtags
    pipeline_data: Optional[dict] = None

class RegenerateSceneRequest(BaseModel):
    scene_index: int = Field(..., ge=0)
    prompt: str

class SceneSourcesUpdate(BaseModel):
    """User-supplied sources for one scene while a job sits at source_review."""
    scene_index: int = Field(..., ge=0)
    fact: Optional[str] = None
    sources: List[SourceRef] = Field(default_factory=list)

class UpdateSceneSourcesRequest(BaseModel):
    scenes: List[SceneSourcesUpdate]

class ThumbnailRequest(BaseModel):
    thumbnail_text: Optional[str] = None


class ContinueRenderRequest(BaseModel):
    job_id: Optional[str] = None

class ApproveJobRequest(BaseModel):
    job_id: Optional[str] = None
    schedule_time: Optional[datetime] = None  # None = post immediately
    platforms: List[str] = ["youtube", "tiktok", "facebook"]

class StepScriptGenerateRequest(BaseModel):
    topic: Optional[str] = None
    art_style: Optional[str] = None
    duration: Optional[int] = 60

class UpdateScriptRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    hashtags: Optional[List[str]] = None
    scenes: List[Dict[str, Any]]

class StepVoiceRequest(BaseModel):
    voice_preset: Optional[str] = None
    engine: Optional[str] = None

class VoiceSceneRequest(BaseModel):
    scene_index: int = Field(..., ge=0)
    text: str
    voice_preset: Optional[str] = None

class StepStoryboardRequest(BaseModel):
    art_style: Optional[str] = None

class StepEffectsRequest(BaseModel):
    chunk_words: Optional[int] = 3
    margin_v: Optional[int] = 180
    font_size: Optional[int] = 44

class StepRenderRequest(BaseModel):
    force: Optional[bool] = False

