from fastapi import FastAPI
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="KitmeK Lesson Generation API",
    description="Real-time NCERT-aligned lesson generation",
    version="1.0.0"
)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    logger.info("Health check called")
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "KitmeK Lesson Generation API"
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "KitmeK Lesson Generation API",
        "documentation": "/docs",
        "health": "/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
