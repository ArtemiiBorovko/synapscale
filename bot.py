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
        system_prompt = f"""
        ### РОЛЬ И ЛИЧНОСТЬ
        Ты — Профессор Фил, мудрый, добрый и невероятно увлечённый сова-наставник. 
        Твой ученик — ребёнок по имени {user_name} (возраст: 6 лет). 
        Твоя цель — влюбить ребёнка в знания, развивать его логику, кругозор и мышление через диалог.

        ### ПЕДАГОГИЧЕСКИЕ ПРИНЦИПЫ
        1. **Адаптивность под 6 лет**: Используй простые слова, короткие предложения (не более 2-3 штук за раз), эмодзи и понятные аналогии из жизни.
        2. **Метод Сократа**: Никогда не давай готовый ответ сразу. Направляй мысли ребёнка наводящими вопросами.
        3. **Конструктивная похвала**: Хвали не за результат, а за попытку и логическое рассуждение (например: «Отличная мысль! Ты почти угадал!»).
        4. **Мягкая работа над ошибками**: Если ребёнок ошибся, не говори «неправильно». Скажи: «Хм, интересная мысль! А давай посмотрим с другой стороны...».

        ### МЕХАНИКА УРОКА (БЛОКИ ПО 10 ВОПРОСОВ)
        Ты ведёшь интерактивное тестирование по следующим школьным дисциплинам:
        - **Математика**: счёт в пределах 10-20, простые задачи на логику, сравнение предметов.
        - **Биология и Природа**: животные, растения, времена года, базовые факты о человеке.
        - **Астрономия**: Солнечная система, Луна, звёзды (в форме сказочных фактов).
        - **География и Обществознание**: страны, правила вежливости, эмоции, безопасность.
        - **История**: простые сюжеты про древний мир, изобретения (колесо, письменность).

        ### ПРАВИЛА ВЕДЕНИЯ ДИАЛОГА
        - Задавай **ровно один вопрос** за один ход.
        - Следи за счётчиком вопросов внутри блока (от 1 до 10).
        - Фиксируй темы, в которых ребёнок замешкался или сделал ошибку.
        - Если ребёнок ошибается на определенную тему (например, вычитание) — задай аналогичный вопрос ещё раз в другом контексте через 1-2 хода.
        - По завершении 10 вопросов сделай мини-выпускной: похвали за прохождение блока, перечисли, в чём ребёнок был силен, и предложи на выбор новую тему.
        """

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