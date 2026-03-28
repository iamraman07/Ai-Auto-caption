import os
import subprocess
import uuid
import logging
import imageio_ffmpeg
from app.core.config import OUTPUTS_DIR

logger = logging.getLogger(__name__)

def burn_subtitles(video_path: str, srt_path: str, style_options: dict = None) -> str:
    """
    Burn SRT subtitles into a video file using FFmpeg overlay.
    """
    logger.info(f"Targeting video path for overlay: {video_path}")
    logger.info(f"Targeting subtitle path: {srt_path}")
    
    if not os.path.exists(video_path):
        logger.error(f"Missing video file at: {video_path}")
        raise FileNotFoundError(f"Video file not found at {video_path}")
    if not os.path.exists(srt_path):
        logger.error(f"Missing subtitle file at: {srt_path}")
        raise FileNotFoundError(f"Subtitle file not found at {srt_path}")
        
    base_name = os.path.basename(video_path)
    file_name_without_ext = os.path.splitext(base_name)[0]
    
    # Generate unique filename to avoid overwriting files
    unique_id = uuid.uuid4().hex[:6]
    output_filename = f"{file_name_without_ext}_subtitled_{unique_id}.mp4"
    output_video_path = str(OUTPUTS_DIR / output_filename)
    
    # FFmpeg subtitles filter has notoriously buggy parsing of Windows absolute paths
    # (colons, backslashes, spaces) because it treats them as filter delimiters.
    # We bypass this entirely by running FFmpeg INSIDE the subtitles folder,
    # so we only have to pass the raw filename to the filter!
    srt_dir = os.path.dirname(srt_path)
    srt_filename = os.path.basename(srt_path)
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    
    # Render Force Styles for FFmpeg ASS Subtitle Engine
    vf_filter = f"subtitles='{srt_filename}'"
    
    if style_options:
        force_style_parts = []
        
        # Build Font Size
        font_size = style_options.get("font_size", 24)
        force_style_parts.append(f"Fontsize={font_size}")
        
        # Cross-code Colors (HTML #112233 -> ASS &H00332211&)
        color_hex = style_options.get("color", "#FFFFFF").replace("#", "")
        if len(color_hex) == 6:
            r = color_hex[0:2]
            g = color_hex[2:4]
            b = color_hex[4:6]
            # format: &H00<BB><GG><RR>&
            ass_color = f"&H00{b}{g}{r}&" 
            force_style_parts.append(f"PrimaryColour={ass_color}")
            
        # Parse Font weights
        is_bold = style_options.get("bold", True)
        is_italic = style_options.get("italic", False)
        force_style_parts.append(f"Bold={1 if is_bold else 0}")
        force_style_parts.append(f"Italic={1 if is_italic else 0}")
        
        # Override Default Borders slightly to match modern aesthetic
        force_style_parts.append("BorderStyle=1")
        force_style_parts.append("Outline=1")
        force_style_parts.append("Shadow=1")
        force_style_parts.append("MarginV=20")
        
        force_style_str = ",".join(force_style_parts)
        vf_filter += f":force_style='{force_style_str}'"
        
    command = [
        ffmpeg_exe,
        "-i", video_path,
        "-vf", vf_filter,
        "-c:a", "aac",             # Safely re-encode audio to AAC to guarantee MP4 container compatibility
        "-y",                      # Overwrite if exists
        output_video_path
    ]
    
    try:
        logger.info(f"Executing FFmpeg subtitle overlay... Output target: {output_video_path}")
        subprocess.run(command, cwd=srt_dir, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logger.info("FFmpeg subtitle rendering complete.")
        return output_video_path
    except subprocess.CalledProcessError as e:
        raise Exception(f"FFmpeg failed to burn subtitles: {e.stderr.decode()}")
