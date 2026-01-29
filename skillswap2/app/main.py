from fastapi import FastAPI
from fastapi.responses import FileResponse

from app.api import auth, users, skill
from app.api import skill   # this file exists so import directly

app = FastAPI()

# --------- HTML Pages ----------

@app.get("/")
def home():
    return FileResponse("app/static/login.html")

@app.get("/login")
def login_page():
    return FileResponse("app/static/login.html")

@app.get("/register")
def register_page():
    return FileResponse("app/static/register.html")

@app.get("/add-skill")
def add_skill_page():
    return FileResponse("app/static/add-skill.html")


# --------- API Routers ----------

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(skill.router)
