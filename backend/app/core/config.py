import os
from pathlib import Path

# Define base project directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Define directories
UPLOAD_DIR = BASE_DIR / "uploads"
DOWNLOAD_DIR = BASE_DIR / "downloads"
AUDIO_DIR = BASE_DIR / "audio"
SUBTITLES_DIR = BASE_DIR / "subtitles"
OUTPUTS_DIR = BASE_DIR / "outputs"

# Ensure directories exist
for dir_path in [UPLOAD_DIR, DOWNLOAD_DIR, AUDIO_DIR, SUBTITLES_DIR, OUTPUTS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)
