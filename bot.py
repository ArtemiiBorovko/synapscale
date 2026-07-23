import os
from fastapi import FastAPI, Request
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

@app.get("/")
async def read_root():
    return FileResponse("index.html")

@app.get("/script.js")
async def get_script():
    return FileResponse("script.js")

@app.get("/style.css")
async def get_style():
    return FileResponse("style.css")

@app.get("/api/health")
def health_check():
    return {"status": "healthy"}

# НОВЫЙ БЛОК: Прием сообщений от пользователя
@app.post("/api/chat")
async def chat_with_robot(request: Request):
    data = await request.json()
    user_text = data.get("text", "")
    user_name = data.get("name", "Студент")
    
    # Пока что сервер просто возвращает заглушку. 
    # Позже сюда мы подключим Groq, чтобы робот отвечал умно.
    reply = f"Угу-угу, {user_name}! Я услышал, что ты сказал: «{user_text}». Скоро я научусь отвечать на сложные вопросы!"
    
    return {"reply": reply}
