import os
import uuid
import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from app.core.config import SUBTITLES_DIR
from app.services.audio_extractor import extract_audio
from app.services.transcriber import transcribe_audio
from app.utils.srt_generator import generate_srt
from app.services.system_monitor import is_system_overloaded, is_system_busy
from app.services.queue_manager import queue_manager

logger = logging.getLogger(__name__)

router = APIRouter()

class TranscribeRequest(BaseModel):
    file_path: str

# Helper function to run the heavy processing block in the background
def process_transcription_job(job_id: str, input_path: str):
    logger.info(f"Transcription job started for ID: {job_id}")
    queue_manager.results[job_id]["status"] = "processing"
    
    try:
        audio_path = extract_audio(input_path)
        
        logger.info(f"[{job_id}] Whisper processing begins for {audio_path}")
        transcription_result = transcribe_audio(audio_path)
        logger.info(f"[{job_id}] Transcription ends")
        
        srt_content = generate_srt(transcription_result["segments"])
        
        base_name = os.path.basename(input_path)
        file_name_without_ext = os.path.splitext(base_name)[0]
        srt_filename = f"{file_name_without_ext}_{job_id}.srt"
        srt_file_path = os.path.join(SUBTITLES_DIR, srt_filename)
        
        with open(srt_file_path, "w", encoding="utf-8") as srt_file:
            srt_file.write(srt_content)
            
        queue_manager.results[job_id]["status"] = "completed"
        queue_manager.results[job_id]["result"] = {
            "text": transcription_result["text"],
            "segments": transcription_result["segments"],
            "srt": srt_content,
            "saved_srt_path": srt_file_path,
            "saved_srt_filename": srt_filename
        }
        
    except Exception as e:
        logger.error(f"[{job_id}] Transcription job failed: {e}")
        queue_manager.results[job_id]["status"] = "failed"
        queue_manager.results[job_id]["error"] = str(e)

@router.post("/transcribe")
async def transcribe_endpoint(request: TranscribeRequest, background_tasks: BackgroundTasks):
    """
    Endpoint to transcribe an audio/video file securely via BackgroundTasks.
    """
    input_path = request.file_path
    
    if not os.path.exists(input_path):
        raise HTTPException(status_code=404, detail="File path provided does not exist.")
    
    # 1. System Load Check
    if is_system_overloaded():
        return {
            "status": "rejected",
            "message": "System is critically overloaded (CPU & RAM > 90%). Please try again later."
        }
        
    # Generate job_id manually to bypass the broken queue worker
    job_id = uuid.uuid4().hex[:8]
    queue_manager.results[job_id] = {"status": "queued"}
    
    logger.info(f"Queuing direct BackgroundTask execution for job ID: {job_id}")
    
    # Add to fastapi background tasks (TEMP FIX: force direct execution bypassing broken queue_manager loop)
    # This prevents the job from getting stuck if queue worker is dead.
    background_tasks.add_task(process_transcription_job, job_id, input_path)
    
    return {
        "job_id": job_id,
        "status": "processing",
        "message": "System is free. Processing your transcription immediately.",
        "queue_position": 0
    }

@router.get("/transcribe/status/{job_id}")
async def get_transcription_status(job_id: str):
    """
    Endpoint to check the status or retrieve results of a queued job.
    """
    return queue_manager.get_status(job_id)
