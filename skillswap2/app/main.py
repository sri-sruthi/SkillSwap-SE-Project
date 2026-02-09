# app/main.py - COMPLETE MAIN FILE
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.api import auth, users, skill, session, search
# Import ALL API routers
from app.api import auth, users, skill, session, search

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(title="SkillSwap API")
APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
# CORS Middleware - MUST be before routers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include ALL API routers - THIS IS CRITICAL!
app.include_router(auth.router)      # /auth/register, /auth/login
app.include_router(users.router)     # /users/me, /users/profile
app.include_router(skill.router)     # /skills/*
app.include_router(session.router)   # /sessions/* - THIS WAS MISSING!
app.include_router(search.router)    # /search/*
app.include_router(auth.router)   # ← MUST BE PRESENT
# Mount static files AFTER API routers
# Get the directory where main.py is located (i.e., app/)


# Static files are inside app/static/


# Root endpoint
@app.get("/")
def root():
    """Redirect to landing page"""
    return RedirectResponse(url="/static/index.html")

# Health check
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "message": "SkillSwap API is running",
        "version": "1.0.0"
    }

# Debug: List all routes (remove in production)
@app.get("/debug/routes")
def list_routes():
    """List all registered routes for debugging"""
    routes = []
    for route in app.routes:
        if hasattr(route, 'methods'):
            routes.append({
                "path": route.path,
                "methods": list(route.methods),
                "name": route.name
            })
    return {"routes": routes}
# In app/main.py
from fastapi.responses import FileResponse

# In app/main.py
from fastapi.responses import FileResponse

@app.get("/register")
async def register_page():
    return FileResponse(STATIC_DIR / "register.html")

