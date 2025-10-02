"""
Main FastAPI application for the earnings copilot system.
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from apps.api.routes_admin import router as admin_router
from apps.api.routes_subscriptions import router as subscriptions_router
from apps.api.routes_public import router as public_router
from services.storage import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    print("Starting earnings copilot API...")
    
    # Initialize database
    await init_db()
    print("Database initialized")
    
    yield
    
    # Shutdown
    print("Shutting down earnings copilot API...")


# Create FastAPI app
app = FastAPI(
    title="Earnings Copilot HFT API",
    description="AI-powered earnings analysis and trading signals",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "status_code": exc.status_code,
            "timestamp": request.state.timestamp if hasattr(request.state, 'timestamp') else None
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    print(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "status_code": 500,
            "error_type": type(exc).__name__
        }
    )


# Middleware to add request timestamp
@app.middleware("http")
async def add_timestamp_middleware(request: Request, call_next):
    """Add timestamp to request state."""
    from datetime import datetime
    request.state.timestamp = datetime.utcnow().isoformat()
    response = await call_next(request)
    return response


# Include routers
app.include_router(admin_router)
app.include_router(subscriptions_router)
app.include_router(public_router)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Earnings Copilot HFT API",
        "version": "1.0.0",
        "description": "AI-powered earnings analysis and trading signals",
        "endpoints": {
            "admin": "/admin/*",
            "subscriptions": "/subscriptions/*",
            "public": "/*",
            "docs": "/docs",
            "redoc": "/redoc"
        },
        "authentication": "X-API-Key header required",
        "status": "operational"
    }


# Development server
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )
