from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import auth, users, skill

app = FastAPI()

# Serve static folder
app.mount("/static", StaticFiles(directory="app/static"), name="static")


# ----------- PAGES ------------

@app.get("/")
def home():
    return FileResponse("app/static/index.html")


@app.get("/login")
def login_page():
    return FileResponse("app/static/login.html")


@app.get("/register")
def register_page():
    return FileResponse("app/static/register.html")


from fastapi.responses import FileResponse

@app.get("/add-skill")
def add_skill():
    return FileResponse("app/static/add-skill.html")

@app.get("/search")
def search():
    return FileResponse("app/static/search.html")



# ----------- APIs ------------

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(skill.router)
