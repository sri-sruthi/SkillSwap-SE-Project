# app/main.py - COMPLETE MAIN FILE
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from app.database import Base, engine
from app.api import auth, notification, recommendation, review, search, session, skill, token, users

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(title="SkillSwap API")
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://0.0.0.0:8000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routers
app.include_router(auth.router)          # /auth/*
app.include_router(users.router)         # /users/*
app.include_router(skill.router)         # /skills/*
app.include_router(session.router)       # /sessions/*
app.include_router(search.router)        # /search/*
app.include_router(review.router)        # /reviews/*
app.include_router(notification.router)  # /notifications/*
app.include_router(token.router)
app.include_router(recommendation.router)

@app.get("/")
def root():
    """Redirect to landing page."""
    return RedirectResponse(url="/static/index.html")


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "message": "SkillSwap API is running",
        "version": "1.0.0",
    }


@app.get("/debug/routes")
def list_routes():
    """List all registered routes for debugging."""
    routes = []
    for route in app.routes:
        if hasattr(route, "methods"):
            routes.append({
                "path": route.path,
                "methods": list(route.methods),
                "name": route.name,
            })
    return {"routes": routes}


@app.get("/register")
async def register_page():
    return FileResponse(STATIC_DIR / "register.html")


@app.get("/login")
async def login_page():
    return FileResponse(STATIC_DIR / "login.html")


@app.get("/admin/login")
async def admin_login_page():
    return FileResponse(STATIC_DIR / "admin-login.html")


@app.get("/admin/dashboard")
async def admin_dashboard_page():
    return FileResponse(STATIC_DIR / "admin-dashboard.html")
