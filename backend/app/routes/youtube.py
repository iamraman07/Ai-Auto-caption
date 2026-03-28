import os
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import uuid
from app.core.config import DOWNLOAD_DIR
from app.services.audio_extractor import extract_audio
import yt_dlp

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

router = APIRouter()

class YouTubeRequest(BaseModel):
    url: str

@router.post("/youtube")
async def download_youtube_video(request: YouTubeRequest):
    """
    Endpoint to download a YouTube video and extract its audio.
    """
    url = request.url
    if not url:
        raise HTTPException(status_code=400, detail="YouTube URL is required")
        
    # Create a safe, URL-friendly filename structure avoiding random special characters
    safe_name = f"yt_video_{uuid.uuid4().hex[:8]}"
    output_template = os.path.join(DOWNLOAD_DIR, f"{safe_name}.%(ext)s")
    
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': output_template,
        'merge_output_format': 'mp4', # Enforce MP4 container heavily
        'quiet': False, # Allow printing download progress to terminal
        'no_warnings': True,
    }
    
    try:
        logger.info(f"Starting YouTube download for URL: {url}")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract info and download in one step natively
            info_dict = ydl.extract_info(url, download=True)
            downloaded_file_path = ydl.prepare_filename(info_dict)
            
            # yt-dlp might merge to MKV/WEBM if MP4/M4A merge fails cleanly
            if not os.path.exists(downloaded_file_path):
                base, ext = os.path.splitext(downloaded_file_path)
                for new_ext in [".mkv", ".webm"]:
                    if os.path.exists(base + new_ext):
                        downloaded_file_path = base + new_ext
                        break
                        
        logger.info(f"Successfully downloaded YouTube video: {downloaded_file_path}")
        
    except Exception as e:
        logger.error(f"YouTube download failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to download YouTube video: {str(e)}")
        
    # Extract audio using the extracted file path
    try:
        audio_path = extract_audio(downloaded_file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract audio from YouTube download: {str(e)}")
        
    return {
        "message": "YouTube video downloaded and audio extracted successfully",
        "video_path": downloaded_file_path,
        "audio_path": audio_path
    }
