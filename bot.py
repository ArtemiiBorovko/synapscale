import os
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Отдаем HTML страницу
@app.get("/")
async def read_root():
    return FileResponse("index.html")

# Отдаем скрипты
@app.get("/script.js")
async def get_script():
    return FileResponse("script.js")

# Отдаем стили
@app.get("/style.css")
async def get_style():
    return FileResponse("style.css")

@app.get("/api/health")
def health_check():
    return {"status": "healthy"}
