import os
import shutil
from fastapi import APIRouter, File, UploadFile, HTTPException
from app.core.config import UPLOAD_DIR
from app.services.audio_extractor import extract_audio

router = APIRouter()

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Endpoint to handle direct file uploads (video or audio).
    """
    # 1. Validate file (Optional but good practice)
    allowed_content_types = ["video/mp4", "video/x-matroska", "audio/mpeg", "audio/wav", "video/quicktime"]
    if file.content_type not in allowed_content_types:
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a valid video or audio file.")
        
    # 2. Save the file to the /uploads folder
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
        
    # 3. Extract audio automatically after saving
    try:
        audio_path = extract_audio(file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract audio: {str(e)}")

    return {
        "message": "File uploaded and audio extracted successfully",
        "saved_path": file_path,
        "audio_path": audio_path
    }
