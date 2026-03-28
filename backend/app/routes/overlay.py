from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import os
import uuid
import logging

from app.services.video_processor import burn_subtitles
from app.utils.srt_generator import generate_srt
from app.core.config import SUBTITLES_DIR

logger = logging.getLogger(__name__)

router = APIRouter()

class Segment(BaseModel):
    start: float
    end: float
    text: str

class StyleOptions(BaseModel):
    font_size: int = 24
    color: str = "#ffffff"
    bold: bool = True
    italic: bool = False

class OverlayRequest(BaseModel):
    video_path: str
    srt_path: Optional[str] = None
    segments: Optional[List[Segment]] = None
    style: Optional[StyleOptions] = None

@router.post("/overlay")
async def overlay_subtitles(request: OverlayRequest):
    """
    Endpoint to overlay an SRT file onto a video.
    If 'segments' are provided, we dynamically build a fresh SRT file to capture user live edits!
    """
    logger.info(f"Incoming /overlay request targeting video path: {request.video_path}")
    try:
        if request.segments:
            # Rebuild the SRT formatted text from the live frontend array
            # We convert Pydantic Segment models safely using .model_dump() or dict() 
            # Depending on pydantic version, dict() is safest backwards-compatible way
            srt_content = generate_srt([seg.dict() for seg in request.segments])
            unique_id = uuid.uuid4().hex[:6]
            target_srt = os.path.join(SUBTITLES_DIR, f"edited_{unique_id}.srt")
            with open(target_srt, "w", encoding="utf-8") as f:
                f.write(srt_content)
        elif request.srt_path:
            target_srt = request.srt_path
        else:
            raise HTTPException(status_code=400, detail="Must provide either srt_path or segments.")

        style_dict = request.style.dict() if request.style else None
        output_path = burn_subtitles(request.video_path, target_srt, style_dict)
        
        # Format the URL so the frontend can load it synchronously in a <video> element
        filename = os.path.basename(output_path)
        video_url = f"http://127.0.0.1:8000/outputs/{filename}"
        
        return {
            "message": "Subtitles successfully embedded into the video.",
            "output_video_path": output_path,
            "video_url": video_url
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
