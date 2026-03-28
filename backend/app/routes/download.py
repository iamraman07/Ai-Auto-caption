import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from app.core.config import SUBTITLES_DIR

router = APIRouter()

@router.get("/download-srt")
async def download_srt(filename: str):
    """
    Endpoint to download a generated SRT file.
    """
    # Create the full path to the requested file
    file_path = os.path.join(SUBTITLES_DIR, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Subtitle file not found.")
        
    # FileResponse handles streaming the download to the browser securely
    return FileResponse(
        path=file_path, 
        filename=filename, 
        media_type='application/x-subrip'
    )
