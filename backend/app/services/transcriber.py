import whisper
import os
import shutil
import logging
from pathlib import Path
import imageio_ffmpeg
from app.core.config import BASE_DIR
from app.utils.text_cleaner import clean_hinglish_text
from app.utils.srt_generator import split_segments

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Deep Magic: Whisper hardcodes its audio loading to use exactly 'ffmpeg' as the command string.
# Since imageio_ffmpeg names its binary 'ffmpeg-win64-v4.2.2.exe', Windows doesn't match them!
# We will copy and safely rename the embedded binary into our backend/bin folder, 
# and add that to System PATH. Completely portable and offline!

bin_dir = BASE_DIR / "bin"
bin_dir.mkdir(exist_ok=True)
local_ffmpeg = bin_dir / "ffmpeg.exe"

if not local_ffmpeg.exists():
    shutil.copy(imageio_ffmpeg.get_ffmpeg_exe(), str(local_ffmpeg))

os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")

# Global singleton for the model
_MODEL_INSTANCE = None

def get_whisper_cache_dir() -> Path:
    """Returns the default Whisper cache directory path."""
    return Path.home() / ".cache" / "whisper"

def clear_whisper_cache():
    """Deletes the whisper cache folder if it exists to fix corrupted downloads."""
    cache_dir = get_whisper_cache_dir()
    if cache_dir.exists() and cache_dir.is_dir():
        logger.warning(f"Clearing Whisper cache at {cache_dir} due to corruption/load failure...")
        try:
            shutil.rmtree(cache_dir)
            logger.info("Whisper cache cleared successfully. Ready for clean re-download.")
        except Exception as e:
            logger.error(f"Failed to clear Whisper cache: {e}")

def load_whisper_model(model_name: str):
    """Attempts to load a specific Whisper model, with cache-clearing on hash mismatch."""
    logger.info(f"Attempting to load Whisper model '{model_name}'...")
    try:
        loaded_model = whisper.load_model(model_name)
        logger.info(f"Model '{model_name}' loaded successfully.")
        return loaded_model
    except Exception as e:
        error_str = str(e).lower()
        if "hash mismatch" in error_str or "checksum" in error_str or "corrupt" in error_str or "eof" in error_str:
            logger.error(f"Corruption detected for model '{model_name}': {e}")
            clear_whisper_cache()
            
            logger.info(f"Retrying download and load for model '{model_name}'...")
            try:
                loaded_model = whisper.load_model(model_name)
                logger.info(f"Model '{model_name}' loaded successfully after cache clear.")
                return loaded_model
            except Exception as retry_e:
                logger.error(f"Failed to load '{model_name}' even after clearing cache: {retry_e}")
                raise retry_e
        else:
            logger.error(f"Unexpected error loading '{model_name}': {e}")
            raise e

def get_model():
    """
    Returns the globally loaded Whisper model.
    Implements a singleton pattern to prevent multiple loads during FastAPI reloads.
    """
    global _MODEL_INSTANCE
    if _MODEL_INSTANCE is not None:
        return _MODEL_INSTANCE
        
    logger.info("Initializing Whisper model engine...")
    try:
        _MODEL_INSTANCE = load_whisper_model("large-v3")
    except Exception as e:
        logger.warning(f"Fallback triggered: Failed to load 'large-v3' ({e})")
        try:
            _MODEL_INSTANCE = load_whisper_model("medium")
        except Exception as fallback_e:
            logger.critical(f"CRITICAL: Failed to load fallback 'medium' model: {fallback_e}")
            _MODEL_INSTANCE = None
            
    return _MODEL_INSTANCE

# Initialize model eagerly so it's ready before the first request
_MODEL_INSTANCE = get_model()

def transcribe_audio(audio_path: str) -> dict:
    """
    Transcribes an audio file using the globally loaded Whisper model.
    Returns the transcription result including text and segments.
    """
    global_model = get_model()
    if not global_model:
        raise RuntimeError("Whisper model is not loaded correctly.")

    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found at {audio_path}")

    # The transcribe method processes the audio file and returns 
    # a dict containing 'text', 'segments', 'language', etc.
    try:
        # fp16=False prevents warnings on CPU execution.
        # Setting temperature=0, beam_size=5, best_of=5 for stable output.
        # Using initial_prompt to guide Hinglish transcription without hard-locking language="hi".
        result = global_model.transcribe(
            audio_path, 
            task="transcribe", 
            fp16=False,
            temperature=0,
            beam_size=5,
            best_of=5,
            initial_prompt="This is a Hinglish conversation with Hindi and English mixed naturally.",
            no_speech_threshold=0.6,
            logprob_threshold=-1.0,
            condition_on_previous_text=False
        )
        
        # Clean Output Text:
        cleaned_segments = []
        last_text = ""
        
        for segment in result.get("segments", []):
            # Silence Filtering: Ignore low-confidence or silent segments where no_speech_prob > 0.6
            if segment.get("no_speech_prob", 0) > 0.6:
                continue
                
            text = segment["text"].strip()
            # Pass through our Hinglish post-processing and text cleaning
            text = clean_hinglish_text(text)
            
            # Cross-segment repetition filter (Whisper loop prevention)
            if text.lower() == last_text.lower() and len(text) > 0:
                continue
                
            if not text:
                continue
                
            last_text = text
            
            cleaned_segments.append({
                "start": float(segment["start"]),
                "end": float(segment["end"]),
                "text": text
            })
            
        # Apply subtitle line splitting correctly formatted
        split_seg = split_segments(cleaned_segments)
        
        return {
            "text": " ".join([seg["text"] for seg in split_seg]),
            "segments": split_seg
        }
    except Exception as e:
        raise Exception(f"Transcription failed: {str(e)}")
