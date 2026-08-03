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

@app.post("/api/chat")
async def chat_with_robot(request: Request):
    try:
        data = await request.json()
        user_name = data.get("name", "Друг")
        chat_history = data.get("history", [])
        
        if not chat_history:
            return {"reply": "Ты ничего не написал! Попробуй еще раз."}
            
        if not groq_client:
            return {"reply": f"Привет, {user_name}! Я профессор Фил, но у меня не настроен ключ Groq API."}

        # --- ОБНОВЛЕННЫЙ СИСТЕМНЫЙ ПРОМПТ ---
        system_prompt = (
            f"Ты — профессор Фил, умная и добрая сова-наставник. Твой ученик — ребенок 6 лет по имени {user_name}. "
            f"Твоя задача — проводить уроки в формате блоков по 10 вопросов.\n\n"
            f"ПРАВИЛА:\n"
            f"1. Темы: чередуй базовую математику, биологию, астрономию, географию, обществознание и историю, адаптированные для 6-летки.\n"
            f"2. Задавай строго по одному вопросу. Дождись ответа ребенка, проверь его, мягко объясни правильный ответ и только потом задавай следующий вопрос.\n"
            f"3. Анализируй ошибки: если ребенок ошибся (например, в вычитании или в виде животного), запомни это и в следующем блоке дай больше задач на эту тему для работы над ошибками.\n"
            f"4. Когда блок из 10 вопросов пройден, подведи итоги, похвали и начни новый уникальный блок вопросов.\n"
            f"5. Отвечай коротко (1-3 предложения), тепло и без сложных слов."
        )
        # ------------------------------------

        messages_for_ai = [{"role": "system", "content": system_prompt}]
        for msg in chat_history:
            messages_for_ai.append({"role": msg["role"], "content": msg["content"]})

        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages_for_ai,
            temperature=0.7,
            max_tokens=300
        )
        
        reply = completion.choices[0].message.content
        return {"reply": reply}

    except Exception as e:
        return {"reply": f"Ой, ошибка связи с нейросетью: {str(e)}"}