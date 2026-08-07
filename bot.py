import os
import json
import random
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

# БАЗА ПРЕДМЕТОВ И ПОДТЕМ ДЛЯ ЖЁСТКОЙ РОТАЦИИ НА СТОРOНЕ PYTHON
TOPICS_POOL = {
    "Математика": [
        "Простые задачки на сложение и вычитание",
        "Таблица умножения (простые примеры)",
        "Геометрические фигуры (квадрат, круг, треугольник)",
        "Логические последовательности и узоры",
        "Единицы измерения (сантиметры, килограммы, литры)"
    ],
    "Биология и Природа": [
        "Млекопитающие и их повадки",
        "Насекомые и их секреты",
        "Морские обитатели и рыбы",
        "Растения, деревья и цветы",
        "Перелетные и лесные птицы",
        "Домашние животные и уход за ними"
    ],
    "География и Земля": [
        "Материки и континенты",
        "Реки, озера и водоемы",
        "Горы, вулканы и пещеры",
        "Страны, города и достопримечательности",
        "Погода, облака и времена года"
    ],
    "Астрономия и Космос": [
        "Солнце и Луна",
        "Разнообразие планет Солнечной системы",
        "Созвездия и ночное небо",
        "Космонавты, ракеты и МКС",
        "Астероиды и кометы"
    ],
    "История и Культура": [
        "Древние рыцари и замки",
        "Великие изобретения (колесо, компас, печать)",
        "Древняя Греция и Олимпийские игры",
        "Пирамиды и древние цивилизации",
        "Путешественники и открытие новых земель"
    ],
    "Окружающий мир": [
        "Правила дорожного движения и безопасность",
        "Профессии людей (врач, пожарный, архитектор)",
        "Правильное питание и здоровье",
        "Экология и бережное отношение к природе",
        "Музыкальные инструменты"
    ]
}

def get_db_connection():
    if not DATABASE_URL:
        return None
    try:
        return psycopg2.connect(DATABASE_URL)
    except Exception as e:
        print("Ошибка подключения к БД:", e)
        return None

def init_db():
    conn = get_db_connection()
    if conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS child_profiles (
                    user_name VARCHAR(100) PRIMARY KEY,
                    score INT DEFAULT 0,
                    total_questions INT DEFAULT 0,
                    weak_topics TEXT DEFAULT '{}',
                    recent_subtopics TEXT DEFAULT '[]'
                );
            """)
            cur.execute("""
                ALTER TABLE child_profiles ADD COLUMN IF NOT EXISTS recent_subtopics TEXT DEFAULT '[]';
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

# --- 1. РУЧКА ГЕНЕРАЦИИ ИИ-ВОПРОСА ---
@app.post("/api/get-question")
async def get_question(request: Request):
    try:
        data = await request.json()
        user_name = data.get("name", "Друг").strip()

        score = 0
        weak_dict = {}
        recent_subtopics_list = []

        conn = get_db_connection()
        if conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM child_profiles WHERE LOWER(user_name) = LOWER(%s)", (user_name,))
                user_data = cur.fetchone()
                if not user_data:
                    cur.execute("INSERT INTO child_profiles (user_name, weak_topics, recent_subtopics) VALUES (%s, '{}', '[]')", (user_name,))
                    conn.commit()
                else:
                    score = user_data["score"]
                    try:
                        weak_dict = json.loads(user_data.get("weak_topics") or '{}')
                    except:
                        weak_dict = {}
                    try:
                        recent_subtopics_list = json.loads(user_data.get("recent_subtopics") or '[]')
                    except:
                        recent_subtopics_list = []
            conn.close()

        # 1. Выбор подтемы на стороне Python (Hard Exclusion)
        chosen_topic = None
        chosen_subcategory = None

        active_weak = [k for k, v in weak_dict.items() if v > 0]
        if active_weak:
            weak_key = random.choice(active_weak)
            parts = weak_key.split(": ")
            chosen_topic = parts[0]
            chosen_subcategory = parts[1] if len(parts) > 1 else "Отработка ошибок"
        else:
            available_pairs = []
            for topic, subtopics in TOPICS_POOL.items():
                for sub in subtopics:
                    pair_str = f"{topic}: {sub}"
                    if pair_str not in recent_subtopics_list[-25:]: # Не повторяем последние 25 подтем
                        available_pairs.append((topic, sub))

            if not available_pairs:
                for topic, subtopics in TOPICS_POOL.items():
                    for sub in subtopics:
                        available_pairs.append((topic, sub))

            chosen_topic, chosen_subcategory = random.choice(available_pairs)

        # 2. Формируем промпт с ПРИНУДИТЕЛЬНОЙ подтемой
        system_prompt = f"""
        Ты — профессор Фил, добрый учитель для ребёнка по имени {user_name} (8-9 лет).

        ЗАДАЧА:
        Сгенерируй один УНИКАЛЬНЫЙ и ИНТЕРЕСНЫЙ вопрос СТРОГО по указанной теме.

        ОБЯЗАТЕЛЬНАЯ ТЕМА И ПОДТЕМА:
        - Предмет: {chosen_topic}
        - Узкая подтема: {chosen_subcategory}

        ТРЕБОВАНИЯ К ВОПРОСУ:
        1. Уровень: 2-3 класс (8-9 лет). Понятный детский язык, увлекательный факт.
        2. СТРОГО ЗАПРЕЩЕНО использовать банальные клише ("Какой самый большой океан", "Какая самая большая птица", "Какая самая большая планета"). Придумай нестандартный детский факт по подтеме "{chosen_subcategory}"!
        3. ЯЗЫК: ТОЛЬКО 100% ЧИСТЫЙ РУССКИЙ ЯЗЫК! Никаких иностранных слов.

        ТРЕБОВАНИЯ К ФОРМАТУ (ТОЛЬКО ЧИСТЫЙ VALID JSON):
        {{
            "question": "Интересный вопрос на русском языке...",
            "options": ["Вариант 1", "Вариант 2", "Вариант 3", "Вариант 4"],
            "correctAnswer": "Точный текст правильного ответа",
            "explanation": "Короткое доброе объяснение (1-2 простые фразы)",
            "topic": "{chosen_topic}",
            "subcategory": "{chosen_subcategory}"
        }}
        """

        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": system_prompt}],
            response_format={"type": "json_object"},
            temperature=0.75
        )

        response_content = completion.choices[0].message.content
        question_data = json.loads(response_content)
        question_data["user_score"] = score
        question_data["topic"] = chosen_topic
        question_data["subcategory"] = chosen_subcategory

        # Сохраняем использованную подтему в PostgreSQL
        used_pair = f"{chosen_topic}: {chosen_subcategory}"
        recent_subtopics_list.append(used_pair)
        if len(recent_subtopics_list) > 30:
            recent_subtopics_list = recent_subtopics_list[-30:]

        conn = get_db_connection()
        if conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE child_profiles 
                    SET recent_subtopics = %s 
                    WHERE LOWER(user_name) = LOWER(%s)
                """, (json.dumps(recent_subtopics_list, ensure_ascii=False), user_name))
                conn.commit()
            conn.close()

        return question_data

    except Exception as e:
        print("Ошибка генерации вопроса:", e)
        return {
            "question": "Сколько лапок у двух котиков вместе?",
            "options": ["4", "6", "8", "10"],
            "correctAnswer": "8",
            "explanation": "У каждого котика по 4 лапки: 4 + 4 = 8!",
            "topic": "Математика",
            "subcategory": "Простые задачки на сложение и вычитание",
            "user_score": 0
        }

# --- 2. РУЧКА СОХРАНЕНИЯ РЕЗУЛЬТАТА В NEON ---
@app.post("/api/submit-answer")
async def submit_answer(request: Request):
    try:
        data = await request.json()
        user_name = data.get("name", "").strip()
        is_correct = data.get("is_correct")
        topic = data.get("topic", "Общие знания")
        subcategory = data.get("subcategory", "Разное")

        if not user_name:
            return {"status": "error", "message": "Имя не указано"}

        full_topic_key = f"{topic}: {subcategory}"
        new_score = 0

        conn = get_db_connection()
        if conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT weak_topics FROM child_profiles WHERE LOWER(user_name) = LOWER(%s)", (user_name,))
                row = cur.fetchone()
                
                weak_dict = {}
                if row and row["weak_topics"]:
                    try:
                        weak_dict = json.loads(row["weak_topics"])
                    except:
                        weak_dict = {}

                if is_correct:
                    if full_topic_key in weak_dict:
                        weak_dict[full_topic_key] -= 1
                        if weak_dict[full_topic_key] <= 0:
                            del weak_dict[full_topic_key]
                else:
                    weak_dict[full_topic_key] = weak_dict.get(full_topic_key, 0) + 1

                new_weak_topics_str = json.dumps(weak_dict, ensure_ascii=False)

                if is_correct:
                    cur.execute("""
                        UPDATE child_profiles 
                        SET score = score + 1, total_questions = total_questions + 1, weak_topics = %s
                        WHERE LOWER(user_name) = LOWER(%s) RETURNING score
                    """, (new_weak_topics_str, user_name))
                else:
                    cur.execute("""
                        UPDATE child_profiles 
                        SET total_questions = total_questions + 1, weak_topics = %s
                        WHERE LOWER(user_name) = LOWER(%s) RETURNING score
                    """, (new_weak_topics_str, user_name))
                
                row = cur.fetchone()
                if row:
                    new_score = row["score"]
                conn.commit()
            conn.close()

        return {"status": "ok", "score": new_score}
    except Exception as e:
        print("Ошибка сохранения в базу:", e)
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
        Ты — Профессор Фил, мудрый, добрый сова-наставник для ребёнка {user_name} (8-9 лет).
        Отвечай коротко (1-3 предложения), тепло, понятным языком, используй простые эмодзи.
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