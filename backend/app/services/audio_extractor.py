import os
import subprocess
import imageio_ffmpeg
from app.core.config import AUDIO_DIR

def extract_audio(input_video_path: str) -> str:
    """
    Extracts audio from a video file using FFmpeg.
    Returns the path to the extracted audio file.
    """
    # Create the output audio path based on the input filename
    base_name = os.path.basename(input_video_path)
    file_name_without_ext = os.path.splitext(base_name)[0]
    output_audio_path = os.path.join(AUDIO_DIR, f"{file_name_without_ext}.wav")
    
    # If it's already an audio file, maybe we don't strictly need to convert, 
    # but Standardizing to mp3 ensures Whisper handles it consistently.
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    
    command = [
        ffmpeg_exe,
        "-i", input_video_path,
        "-ac", "1",           # Mono channel
        "-ar", "16000",       # 16kHz sample rate strictly for Whisper
        "-af", "afftdn,loudnorm", # Noise reduction and volume normalization for clarity

        "-y",                 # Overwrite output file if it exists
        output_audio_path
    ]
    
    try:
        # Run FFmpeg command synchronously
        # We capture stdout and stderr to prevent console spam and allow error handling
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return output_audio_path
    except subprocess.CalledProcessError as e:
        # In a real app we would log the error using a logger
        raise Exception(f"FFmpeg failed to extract audio: {e.stderr.decode()}")
    except FileNotFoundError:
        raise Exception("FFmpeg is not installed or not added to system PATH.")
