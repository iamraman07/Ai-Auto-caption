import sys
from pathlib import Path

# Fix python path for direct execution via IDE "Run" button
backend_dir = str(Path(__file__).resolve().parent.parent)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import OUTPUTS_DIR
from app.routes import upload, youtube, transcribe, download, overlay

# Initialize the FastAPI application
app = FastAPI(
    title="Auto Caption API",
    description="Offline AI-powered auto caption backend",
    version="1.0.0"
)

# Allow frontend to preview videos from the outputs folder seamlessly
app.mount("/outputs", StaticFiles(directory=str(OUTPUTS_DIR)), name="outputs")

# Enable CORS for frontend local testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(upload.router, prefix="/api", tags=["Upload"])
app.include_router(youtube.router, prefix="/api", tags=["YouTube"])
app.include_router(transcribe.router, prefix="/api", tags=["Transcribe"])
app.include_router(download.router, prefix="/api", tags=["Download"])
app.include_router(overlay.router, prefix="/api", tags=["Overlay"])

@app.get("/")
async def root():
    """
    Root endpoint to check if the API is running.
    """
    return {"message": "Backend is running"}

@app.get("/health")
async def health_check():
    """
    Health check endpoint to monitor system status.
    Later, we will add psutil here to check CPU and RAM usage.
    """
    return {
        "status": "healthy",
        "message": "System is operational"
    }

if __name__ == "__main__":
    import uvicorn
    # Run the FastAPI app using the uvicorn server
    # We specify "app.main:app" string so reloading works correctly
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
