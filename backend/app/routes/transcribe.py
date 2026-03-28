import os
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core.config import SUBTITLES_DIR
from app.services.audio_extractor import extract_audio
from app.services.transcriber import transcribe_audio
from app.utils.srt_generator import generate_srt
from app.services.system_monitor import is_system_overloaded, is_system_busy
from app.services.queue_manager import queue_manager

router = APIRouter()

class TranscribeRequest(BaseModel):
    file_path: str

# Helper function to run the heavy processing block in the background
def process_transcription_job(input_path: str):
    audio_path = extract_audio(input_path)
    transcription_result = transcribe_audio(audio_path)
    srt_content = generate_srt(transcription_result["segments"])
    
    base_name = os.path.basename(input_path)
    file_name_without_ext = os.path.splitext(base_name)[0]
    unique_id = uuid.uuid4().hex[:6]
    srt_filename = f"{file_name_without_ext}_{unique_id}.srt"
    srt_file_path = os.path.join(SUBTITLES_DIR, srt_filename)
    
    with open(srt_file_path, "w", encoding="utf-8") as srt_file:
        srt_file.write(srt_content)
        
    return {
        "text": transcription_result["text"],
        "segments": transcription_result["segments"],
        "srt": srt_content,
        "saved_srt_path": srt_file_path,
        "saved_srt_filename": srt_filename
    }

@router.post("/transcribe")
async def transcribe_endpoint(request: TranscribeRequest):
    """
    Endpoint to transcribe an audio/video file securely via the smart queue.
    """
    input_path = request.file_path
    
    if not os.path.exists(input_path):
        raise HTTPException(status_code=404, detail="File path provided does not exist.")
    
    # 1. System Load Check
    if is_system_overloaded():
        # Case 3: Overloaded -> reject
        return {
            "status": "rejected",
            "message": "System is critically overloaded (CPU & RAM > 90%). Please try again later."
        }
        
    # 2. Check Queue Capacity
    if len(queue_manager.queue) >= queue_manager.max_queue:
        return {
            "status": "rejected",
            "message": "Too many people in line! Queue is full. Try again later."
        }
        
    # 3. Add to background worker queue
    job_id = queue_manager.add_task(process_transcription_job, input_path)
    
    # 4. Intelligent response message
    if is_system_busy():
        status_msg = "queued"
        user_msg = "System under heavy load, processing may be slow"
    elif queue_manager.active_jobs == 0 and len(queue_manager.queue) == 1:
        status_msg = "processing"
        user_msg = "System is free. Processing your transcription immediately."
    else:
        status_msg = "queued"
        user_msg = "Your request is in queue. Please wait."
        
    return {
        "job_id": job_id,
        "status": status_msg,
        "message": user_msg,
        "queue_position": len(queue_manager.queue)
    }

@router.get("/transcribe/status/{job_id}")
async def get_transcription_status(job_id: str):
    """
    Endpoint to check the status or retrieve results of a queued job.
    """
    return queue_manager.get_status(job_id)
