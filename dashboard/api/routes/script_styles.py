"""
Script Style Presets API Route
Provides endpoints to list, retrieve, create, and delete reusable script writing styles.
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from loguru import logger

from core.script_engine.script_style_presets import (
    get_all_script_styles,
    get_script_style_by_id,
    save_script_style,
    delete_script_style
)

router = APIRouter()


class ScriptStyleCreateRequest(BaseModel):
    id: Optional[str] = None
    name: str
    description: Optional[str] = ""
    tone_instruction: str
    target_audience: Optional[str] = ""


@router.get("", response_model=List[dict])
def list_script_styles():
    """Returns all available script style presets."""
    try:
        return get_all_script_styles()
    except Exception as e:
        logger.error(f"Error fetching script styles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{style_id}", response_model=dict)
def get_script_style(style_id: str):
    """Returns a specific script style preset by ID."""
    style = get_script_style_by_id(style_id)
    if not style:
        raise HTTPException(status_code=404, detail="Script style preset not found")
    return style


@router.post("", response_model=dict)
def create_or_update_script_style(req: ScriptStyleCreateRequest):
    """Creates a new script style preset or updates an existing custom one."""
    if not req.name.strip():
        raise HTTPException(status_code=400, detail="Tên phong cách không được để trống")
    if not req.tone_instruction.strip():
        raise HTTPException(status_code=400, detail="Hướng dẫn phong cách (tone instruction) không được để trống")

    style_id = req.id or req.name
    try:
        saved = save_script_style(
            style_id=style_id,
            name=req.name,
            description=req.description or "",
            tone_instruction=req.tone_instruction,
            target_audience=req.target_audience or ""
        )
        return saved
    except Exception as e:
        logger.error(f"Error saving script style: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{style_id}")
def remove_script_style(style_id: str):
    """Deletes a custom script style preset. Built-in styles cannot be deleted."""
    success = delete_script_style(style_id)
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Không thể xoá phong cách mặc định hoặc phong cách không tồn tại"
        )
    return {"ok": True, "message": f"Đã xoá phong cách {style_id}"}
