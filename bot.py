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

def get_db_connection():
    if not DATABASE_URL:
        return None
    try:
        return psycopg2.connect(DATABASE_URL)
    except Exception as e:
        print("Ошибка подключения к БД:", e)
        return None

# Инициализация и автоматическая миграция БД
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
                    recent_questions TEXT DEFAULT '[]'
                );
            """)
            # Добавляем колонку recent_questions, если её не было
            cur.execute("""
                ALTER TABLE child_profiles ADD COLUMN IF NOT EXISTS recent_questions TEXT DEFAULT '[]';
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
        user_name = data.get("name", "Друг").strip()

        score = 0
        weak_dict = {}
        recent_questions_list = []
        
        conn = get_db_connection()
        if conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM child_profiles WHERE LOWER(user_name) = LOWER(%s)", (user_name,))
                user_data = cur.fetchone()
                if not user_data:
                    cur.execute("INSERT INTO child_profiles (user_name, weak_topics, recent_questions) VALUES (%s, '{}', '[]')", (user_name,))
                    conn.commit()
                else:
                    score = user_data["score"]
                    try:
                        weak_dict = json.loads(user_data.get("weak_topics") or '{}')
                    except:
                        weak_dict = {}
                    try:
                        recent_questions_list = json.loads(user_data.get("recent_questions") or '[]')
                    except:
                        recent_questions_list = []
            conn.close()

        # Формируем список слабых тем
        weak_topics_str = "Пока нет ошибок!"
        if weak_dict:
            active_weak_topics = [f"{k} (ошибок: {v})" for k, v in weak_dict.items() if v > 0]
            if active_weak_topics:
                weak_topics_str = ", ".join(active_weak_topics)

        # Подсказка по случайному предмету
        all_subjects = ["Математика", "Биология", "География", "Астрономия", "Обществознание", "История"]
        random_subject_hint = random.choice(all_subjects)

        recent_str = "\n".join([f"- {q}" for q in recent_questions_list[-25:]]) if recent_questions_list else "История вопросов пуста."

        system_prompt = f"""
        Ты — профессор Фил, добрый и увлеченный учитель для ребёнка по имени {user_name}.
        
        ПРОФИЛЬ УЧЕНИКА И СЛОЖНОСТЬ:
        - Возраст/уровень: 8-9 лет (2-3 класс начальной школы). 
        - Вопросы должны быть понятными, детскими, но увлекательными.
        - СТРОГО ЗАПРЕЩЕНЫ: вузовские термины (никакой кинематики, квантовой физики, сложных дат, узких исторический терминов вроде Менеса).
        - ЯЗЫК: ТОЛЬКО 100% ЧИСТЫЙ РУССКИЙ ЯЗЫК! Никаких английских, испанских или латинских слов (никаких "volteo", "Ancient" и т.д.).

        ТЕКУЩИЕ ОШИБКИ И СЛАБЫЕ ТЕМЫ:
        {weak_topics_str}

        ПОСЛЕДНИЕ ЗАДАНИЕ ВОПРОСЫ (КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО ПОВТОРЯТЬ ИХ ИЛИ ИХ ТЕМЫ):
        {recent_str}

        ПРАВИЛА ГЕНЕРАЦИИ:
        1. Если есть активные "Слабые темы", сделай вопрос для их мягкой проработки (в адаптивной детской форме).
        2. Если ошибок нет, выбери предмет "{random_subject_hint}" или любой другой из списка ({', '.join(all_subjects)}) и придумай НОВУЮ детскую тему.
        3. Пример хороших тем для 8-9 лет:
           - Математика: умножение 2x3, простые задачи про яблоки, геометрические фигуры (квадрат, треугольник).
           - Биология: почему зебры полосатые, кто спит зимой, как дыхают рыбы.
           - Астрономия: почему светит Луна, сколько планет (без ухода только в Юпитер!), что такое звезда.
           - География: самый большой океан, где живут пингвины, материки.
           - История: рыцари и замки, как изобрели колесо, древние пирамиды.

        ТРЕБОВАНИЯ К ФОРМАТУ (ТОЛЬКО ЧИСТЫЙ VALID JSON):
        {{
            "question": "Интересный понятный вопрос на русском языке...",
            "options": ["Вариант 1", "Вариант 2", "Вариант 3", "Вариант 4"],
            "correctAnswer": "Точный текст правильного ответа",
            "explanation": "Короткое доброе объяснение (1-2 простые фразы)",
            "topic": "Предмет",
            "subcategory": "Понятная детская подтема"
        }}
        """

        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": system_prompt}],
            response_format={"type": "json_object"},
            temperature=0.6  # Снизили температуру для исключения языковых галлюцинаций
        )

        response_content = completion.choices[0].message.content
        question_data = json.loads(response_content)
        question_data["user_score"] = score

        # Сохраняем сгенерированный вопрос в историю БД
        full_q_title = f"{question_data.get('topic', '')} ({question_data.get('subcategory', '')}): {question_data.get('question', '')}"
        recent_questions_list.append(full_q_title)
        
        # Храним только последние 30 вопросов
        if len(recent_questions_list) > 30:
            recent_questions_list = recent_questions_list[-30:]

        conn = get_db_connection()
        if conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE child_profiles 
                    SET recent_questions = %s 
                    WHERE LOWER(user_name) = LOWER(%s)
                """, (json.dumps(recent_questions_list, ensure_ascii=False), user_name))
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
            "subcategory": "Сложение",
            "user_score": 0
        }

# --- 2. РУЧКА СОХРАНЕНИЯ РЕЗУЛЬТАТА И ОШИБОК В NEON ---
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
        Ты — Профессор Фил, мудрый, добрый и увлечённый сова-наставник для ребёнка {user_name} (8-9 лет).
        Отвечай коротко (1-3 предложения), тепло, понятным языком, стимулируй любознательность и используй простые эмодзи.
        """

        messages_for_ai = [{"role": "system", "content": system_prompt}]
        for msg in chat_history:
            messages_for_ai.append({"role": msg["role"], "content": msg["content"]})

        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": messages_for_ai}],
            temperature=0.7,
            max_tokens=300
        )

        return {"reply": completion.choices[0].message.content}
    except Exception as e:
        return {"reply": f"Ошибка связи с ИИ: {str(e)}"}