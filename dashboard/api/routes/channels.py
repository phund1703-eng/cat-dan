from fastapi import APIRouter, HTTPException
import yaml
import os
from loguru import logger

router = APIRouter()

def load_channels():
    if os.path.exists("channels.yaml"):
        with open("channels.yaml", "r") as f:
            return yaml.safe_load(f)
    return {"channels": []}

@router.get("")
def list_channels():
    return load_channels()

@router.get("/{channel_id}")
def get_channel(channel_id: str):
    data = load_channels()
    for ch in data.get("channels", []):
        if ch.get("id") == channel_id:
            return ch
    raise HTTPException(status_code=404, detail="Channel not found")

@router.get("/{channel_id}/schedule")
def get_channel_schedule(channel_id: str):
    ch = get_channel(channel_id)
    return {"schedule": ch.get("schedule", {})}
