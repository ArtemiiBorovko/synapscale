import os
import json
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
import psycopg2
from psycopg2.extras import RealDictCursor

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

def get_db_connection():
    if not DATABASE_URL:
        return None
    try:
        return psycopg2.connect(DATABASE_URL)
    except Exception as e:
        print("Ошибка подключения к БД:", e)
        return None

# Автоматическая инициализация таблицы при запуске
def init_db():
    conn = get_db_connection()
    if conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS child_profiles (
                    user_name VARCHAR(100) PRIMARY KEY,
                    score INT DEFAULT 0,
                    total_questions INT DEFAULT 0,
                    weak_topics TEXT DEFAULT ''
                );
            """)
            conn.commit()
        conn.close()

init_db()

@app.get("/")
async def read_root():
    return FileResponse("index.html")

@app.get("/script.js")
async def get_script():
    return FileResponse("script.js")

@app.get("/style.css")
async def get_style():
    return FileResponse("style.css")

# --- 1. РУЧКА ГЕНЕРАЦИИ ИИ-ВОПРОСА ДЛЯ КАРТОЧЕК ---
@app.post("/api/get-question")
async def get_question(request: Request):
    try:
        data = await request.json()
        user_name = data.get("name", "Друг")

        score = 0
        weak_topics = ""
        
        # Получаем статистику ребёнка из базы данных Neon
        conn = get_db_connection()
        if conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM child_profiles WHERE user_name = %s", (user_name,))
                user_data = cur.fetchone()
                if not user_data:
                    cur.execute("INSERT INTO child_profiles (user_name) VALUES (%s)", (user_name,))
                    conn.commit()
                else:
                    score = user_data["score"]
                    weak_topics = user_data["weak_topics"]
            conn.close()

        # Формируем инструкцию для генерации JSON-структуры
        system_prompt = f"""
        Ты — профессор Фил, умный учитель для 6-летнего ребёнка по имени {user_name}.
        Сгенерируй один интересный интерактивный вопрос с 4 вариантами ответов.

        КОНТЕКСТ УЧЕНИКА:
        - Текущие очки: {score}
        - Слабые темы (где ребенок ошибался ранее): "{weak_topics if weak_topics else 'пока нет'}".
        Если у ребенка есть слабые темы, сделай упор на них для тренировки.

        ТРЕБОВАНИЯ К ОТВЕТУ:
        Ты должен вернуть ТОЛЬКО валидный JSON-объект без лишнего текста и без markdown-разметки:
        {{
            "question": "Текст вопроса...",
            "options": ["Вариант 1", "Вариант 2", "Вариант 3", "Вариант 4"],
            "correctAnswer": "Точный текст правильного варианта",
            "explanation": "Короткое доброе объяснение (1-2 предложения)",
            "topic": "Название темы (например: Математика, Биология, Астрономия, Логика)"
        }}
        """

        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": system_prompt}],
            response_format={"type": "json_object"},
            temperature=0.7
        )

        response_content = completion.choices[0].message.content
        question_data = json.loads(response_content)
        question_data["user_score"] = score
        return question_data

    except Exception as e:
        print("Ошибка генерации вопроса:", e)
        # Резервный вопрос на случай сбоя API
        return {
            "question": "Сколько лапок у двух котиков вместе?",
            "options": ["4", "6", "8", "10"],
            "correctAnswer": "8",
            "explanation": "У каждого котика по 4 лапки: 4 + 4 = 8!",
            "topic": "Математика",
            "user_score": 0
        }

# --- 2. РУЧКА СОХРАНЕНИЯ РЕЗУЛЬТАТА И ОШИБОК В NEON ---
@app.post("/api/submit-answer")
async def submit_answer(request: Request):
    try:
        data = await request.json()
        user_name = data.get("name")
        is_correct = data.get("is_correct")
        topic = data.get("topic")

        conn = get_db_connection()
        new_score = 0
        if conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if is_correct:
                    cur.execute("""
                        UPDATE child_profiles 
                        SET score = score + 1, total_questions = total_questions + 1 
                        WHERE user_name = %s RETURNING score
                    """, (user_name,))
                else:
                    cur.execute("""
                        UPDATE child_profiles 
                        SET total_questions = total_questions + 1,
                            weak_topics = CASE 
                                WHEN weak_topics LIKE %s THEN weak_topics 
                                ELSE CONCAT(weak_topics, ', ', %s) 
                            END
                        WHERE user_name = %s RETURNING score
                    """, (f"%{topic}%", topic, user_name))
                
                row = cur.fetchone()
                if row:
                    new_score = row["score"]
                conn.commit()
            conn.close()

        return {"status": "ok", "score": new_score}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# --- 3. РУЧКА ОБУЧАЮЩЕГО ЧАТА ---
@app.post("/api/chat")
async def chat_with_robot(request: Request):
    try:
        data = await request.json()
        user_name = data.get("name", "Друг")
        chat_history = data.get("history", [])

        if not chat_history:
            return {"reply": "Ты ничего не написал! Попробуй еще раз."}

        system_prompt = f"""
        Ты — Профессор Фил, мудрый, добрый и увлечённый сова-наставник для ребёнка {user_name} (6 лет).
        Отвечай коротко (1-3 предложения), тепло, стимулируй любознательность и используй простые эмодзи.
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

        return {"reply": completion.choices[0].message.content}
    except Exception as e:
        return {"reply": f"Ошибка связи с ИИ: {str(e)}"}