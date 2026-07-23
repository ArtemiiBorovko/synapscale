import os
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Инициализируем клиента Groq (ключ автоматически берется из настроек Render)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

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

# Эндпоинт для умного чата с профессором Филом через Groq
@app.post("/api/chat")
async def chat_with_robot(request: Request):
    try:
        data = await request.json()
        user_text = data.get("text", "").strip()
        user_name = data.get("name", "Друг")
        
        if not user_text:
            return {"reply": "Ты ничего не написал! Попробуй еще раз."}
            
        if not groq_client:
            return {"reply": f"Привет, {user_name}! Я профессор Фил, но у меня на сервере не настроен ключ Groq API. Добавь его в настройках Render!"}

        # Инструкция для ИИ: как именно должен общаться профессор Фил
        system_prompt = (
            f"Ты — профессор Фил, добрая, умная и веселая сова-наставник, которая обучает детей. "
            f"Твой собеседник — ребенок по имени {user_name}. "
            f"Отвечай коротко (1-3 предложения), тепло, поддерживающе, используя смайлики. "
            f"Объясняй сложные вещи простыми словами, как для ребенка."
        )

        # Отправляем запрос к быстрой и умной модели Llama
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text}
            ],
            temperature=0.7,
            max_tokens=300
        )
        
        reply = completion.choices[0].message.content
        return {"reply": reply}

    except Exception as e:
        return {"reply": f"Ой, у меня в перьях что-то заискрило, ошибка связи с нейросетью: {str(e)}"}
