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
            f"Ты — профессор Фил, добрая, умная и веселая сова-наставник. "
            f"Твой собеседник — ребенок по имени {user_name}. "
            f"Отвечай коротко (1-3 предложения), тепло, поддерживающе. Объясняй всё простыми словами.\n\n"
            f"Твоя главная задача — обучать ребенка через интерактивные игры. Самостоятельно предлагай и проводи одну из следующих игр (чередуй их):\n"
            f"1. Математический квест: задай легкую задачку на счет или логику, встроенную в историю о твоих приключениях в лесу.\n"
            f"2. «Да/Нет» детектив: скажи, что ты загадал животное или предмет. Ребенок должен угадать его, задавая вопросы, а ты можешь отвечать только «Да» или «Нет» (иногда давай маленькие подсказки).\n"
            f"3. Продолжи ряд: напиши закономерность из цифр, букв или эмодзи (например, 🔴 🟦 🔴 🟦 🔴 ...) и попроси угадать следующий элемент.\n\n"
            f"ПРАВИЛА ИГРЫ:\n"
            f"- Веди игру шаг за шагом. Никогда не выдавай правильный ответ сразу.\n"
            f"- Если ребенок ответил неправильно — не ругайся, а дай мягкую наводящую подсказку.\n"
            f"- Когда загадка решена, бурно похвали ребенка и предложи новую игру другого типа."
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