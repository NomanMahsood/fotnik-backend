import sys
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import config

# Add the backend directory to Python path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.append(str(backend_dir))

from app.websockets.routes import router as websocket_router
from app.auth.routes import router as auth_router
from app.product.routes import router as product_router
from app.stats.routes import router as stats_router

app = FastAPI(
    title="Fotnik API",
    description="Backend API for Fotnik application",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080", "http://127.0.0.1:3000", "ws://localhost:8010"],  # Frontend URLs and WebSocket
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include WebSocket routes
app.include_router(websocket_router)
app.include_router(auth_router)
app.include_router(product_router)
app.include_router(stats_router)

# Root endpoint for health check
@app.get("/")
async def root():
    return {"status": "healthy", "message": "Fotnik API is running"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8010, reload=True) 