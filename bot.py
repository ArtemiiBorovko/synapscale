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

TOPICS_POOL = {
    "Математика": [
        "Сложение яблок (до 5)", "Сложение игрушек (до 10)",
        "Вычитание конфет (до 5)", "Вычитание машинок (до 10)",
        "Сравнение: больше или меньше", "Поиск круга",
        "Поиск квадрата", "Поиск треугольника",
        "Счет предметов до 5", "Счет предметов до 10"
    ],
    "Животный мир": [
        "Что едят травоядные", "Что едят хищники",
        "Кто живет в лесу", "Кто живет на ферме",
        "Звуки домашних животных", "Звуки диких животных",
        "Кто спит зимой", "Лесные птицы",
        "Домашние питомцы", "Насекомые"
    ],
    "География и Земля": [
        "Признаки зимы", "Признаки лета",
        "Признаки осени", "Признаки весны",
        "Дождь и лужи", "Снег и лед",
        "Радуга", "Жаркие страны",
        "Северный полюс", "Солнце и Луна"
    ],
    "Окружающий мир": [
        "Сигналы светофора", "Профессия: Врач",
        "Профессия: Повар", "Профессия: Строитель",
        "Сладкие фрукты", "Овощи",
        "Наземный транспорт", "Летающий транспорт",
        "Водный транспорт", "Одежда по погоде"
    ]
}

def get_db_connection():
    if not DATABASE_URL:
        print("ВНИМАНИЕ: DATABASE_URL не задана!")
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
                    recent_subtopics TEXT DEFAULT '[]',
                    recent_questions TEXT DEFAULT '[]'
                );
            """)
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

# --- 1. ГЕНЕРАЦИЯ ВОПРОСА С ЖЕСТКИМ ФИЛЬТРОМ ПОВТОРОВ ---
@app.post("/api/get-question")
async def get_question(request: Request):
    try:
        data = await request.json()
        # Нормализуем имя (убираем пробелы и приводим к нижнему регистру для базы)
        user_name = data.get("name", "Друг").strip().lower()
        display_name = data.get("name", "Друг").strip()

        score = 0
        weak_dict = {}
        recent_subtopics_list = []
        recent_questions_list = []

        conn = get_db_connection()
        if conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM child_profiles WHERE user_name = %s", (user_name,))
                user_data = cur.fetchone()
                if not user_data:
                    cur.execute("""
                        INSERT INTO child_profiles (user_name, score, total_questions, weak_topics, recent_subtopics, recent_questions) 
                        VALUES (%s, 0, 0, '{}', '[]', '[]')
                        ON CONFLICT (user_name) DO NOTHING
                    """, (user_name,))
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
                    try:
                        recent_questions_list = json.loads(user_data.get("recent_questions") or '[]')
                    except:
                        recent_questions_list = []
            conn.close()

        active_weak = [k for k, v in weak_dict.items() if v > 0 and k not in recent_subtopics_list[-3:]]
        
        if active_weak and random.random() < 0.3:
            weak_key = random.choice(active_weak)
            parts = weak_key.split(": ")
            chosen_topic = parts[0]
            chosen_subcategory = parts[1] if len(parts) > 1 else "Отработка ошибок"
        else:
            available_pairs = []
            for topic, subtopics in TOPICS_POOL.items():
                for sub in subtopics:
                    pair_str = f"{topic}: {sub}"
                    if pair_str not in recent_subtopics_list[-20:]: 
                        available_pairs.append((topic, sub))

            if not available_pairs:
                for topic, subtopics in TOPICS_POOL.items():
                    for sub in subtopics:
                        available_pairs.append((topic, sub))

            chosen_topic, chosen_subcategory = random.choice(available_pairs)

        forbidden_questions_text = "\n".join([f"- {q}" for q in recent_questions_list[-25:]])

        system_prompt = f"""
        Ты — профессор Фил, добрый учитель для ребёнка 6 лет. Имя ученика: {display_name}.
        
        ЗАДАЧА:
        Сгенерируй ОЧЕНЬ ПРОСТОЙ детский вопрос по теме: "{chosen_topic}" (подтема: "{chosen_subcategory}").
        
        КРИТИЧЕСКИ ВАЖНО (ЗАПРЕТ НА ПОВТОРЫ):
        Ни в коем случае не создавай вопросы, которые уже есть в списке запрещенных ниже:
        {forbidden_questions_text}
        Придумай абсолютно новый, уникальный вопрос!

        ЖЕСТКИЕ ПРАВИЛА:
        1. ЯЗЫК: ТОЛЬКО 100% русский язык.
        2. ВОЗРАСТ 6 ЛЕТ: Вопросы житейские и понятные.
        3. МАТЕМАТИКА: Если это математика — ТОЛЬКО одно действие (до 10).
        4. ПРОВЕРКА: Правильный ответ ОБЯЗАТЕЛЬНО должен быть среди массива "options".

        ТРЕБОВАНИЯ К ФОРМАТУ (ТОЛЬКО ЧИСТЫЙ VALID JSON):
        {{
            "question": "Короткий простой вопрос...",
            "options": ["Вариант 1", "Вариант 2", "Вариант 3", "Вариант 4"],
            "correctAnswer": "Точный текст правильного ответа",
            "explanation": "Доброе короткое объяснение (1 фраза)",
            "topic": "{chosen_topic}",
            "subcategory": "{chosen_subcategory}"
        }}
        """

        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": system_prompt}],
            response_format={"type": "json_object"},
            temperature=0.8
        )

        question_data = json.loads(completion.choices[0].message.content)
        question_text = question_data.get("question", "")

        question_data["user_score"] = score
        question_data["topic"] = chosen_topic
        question_data["subcategory"] = chosen_subcategory

        used_pair = f"{chosen_topic}: {chosen_subcategory}"
        recent_subtopics_list.append(used_pair)
        if len(recent_subtopics_list) > 25:
            recent_subtopics_list = recent_subtopics_list[-25:]

        if question_text:
            recent_questions_list.append(question_text)
            if len(recent_questions_list) > 25:
                recent_questions_list = recent_questions_list[-25:]

        conn = get_db_connection()
        if conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE child_profiles 
                    SET recent_subtopics = %s, recent_questions = %s
                    WHERE user_name = %s
                """, (
                    json.dumps(recent_subtopics_list, ensure_ascii=False),
                    json.dumps(recent_questions_list, ensure_ascii=False),
                    user_name
                ))
                conn.commit()
            conn.close()

        return question_data

    except Exception as e:
        print("Ошибка генерации вопроса:", e)
        return {
            "question": "Сколько лапок у котика?",
            "options": ["2", "4", "6", "8"],
            "correctAnswer": "4",
            "explanation": "У котика 4 лапки, чтобы быстро бегать!",
            "topic": "Животный мир",
            "subcategory": "Домашние питомцы",
            "user_score": 0
        }

# --- 2. ЖЕЛЕЗОБЕТОННОЕ СОХРАНЕНИЕ ОЧКОВ ---
@app.post("/api/submit-answer")
async def submit_answer(request: Request):
    try:
        data = await request.json()
        print("\n--- ОТЛАДКА СОХРАНЕНИЯ ОТВЕТА ---")
        print("Получено от фронтенда:", data)
        
        user_name = data.get("name", "").strip().lower()
        is_correct = data.get("is_correct")
        print(f"is_correct: {is_correct} (тип: {type(is_correct)})")
        
        if isinstance(is_correct, str):
            is_correct = is_correct.lower() in ("true", "1", "yes")
            
        topic = data.get("topic", "Общие знания")
        subcategory = data.get("subcategory", "Разное")

        if not user_name:
            return {"status": "error", "message": "Имя не указано"}

        full_topic_key = f"{topic}: {subcategory}"
        new_score = 0

        conn = get_db_connection()
        if conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Проверим, что сейчас в базе для этого юзера
                cur.execute("SELECT score, weak_topics FROM child_profiles WHERE user_name = %s", (user_name,))
                row = cur.fetchone()
                print("Текущая запись в БД до обновления:", row)
                
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
                score_increment = 1 if is_correct else 0
                print(f"Прибавка к очкам (score_increment): {score_increment}")
                
                # Используем COALESCE чтобы избежать проблем с NULL в базе
                cur.execute("""
                    INSERT INTO child_profiles (user_name, score, total_questions, weak_topics, recent_subtopics, recent_questions)
                    VALUES (%s, %s, 1, %s, '[]', '[]')
                    ON CONFLICT (user_name) 
                    DO UPDATE SET 
                        score = COALESCE(child_profiles.score, 0) + %s,
                        total_questions = COALESCE(child_profiles.total_questions, 0) + 1,
                        weak_topics = %s
                    RETURNING score;
                """, (user_name, score_increment, new_weak_topics_str, score_increment, new_weak_topics_str))
                
                updated_row = cur.fetchone()
                print("Строка после выполнения SQL (RETURNING):", updated_row)
                
                if updated_row and updated_row["score"] is not None:
                    new_score = updated_row["score"]
                conn.commit()
            conn.close()

        print(правляющий_текст := f"Итоговый счетец для отправки на фронт: {new_score}")
        print("-----------------------------------")
        return {"status": "ok", "score": new_score}
    except Exception as e:
        print("Ошибка сохранения в базу:", e)
        return {"status": "error", "message": str(e)}

# --- 3. ЧАТ С ИИ ---
@app.post("/api/chat")
async def chat_with_robot(request: Request):
    try:
        data = await request.json()
        user_name = data.get("name", "Друг")
        chat_history = data.get("history", [])

        if not chat_history:
            return {"reply": "Ты ничего не написал! Попробуй еще раз."}

        system_prompt = f"""
        Ты — Профессор Фил, добрый наставник для ребёнка 6 лет. Имя ученика: {user_name}.
        Отвечай коротко (1-3 предложения), тепло, используй очень простой детский язык и эмодзи.
        СТРОГО ЗАПРЕЩЕНО использовать любые языки кроме русского.
        """

        messages_for_ai = [{"role": "system", "content": system_prompt}]
        for msg in chat_history:
            messages_for_ai.append({"role": msg["role"], "content": msg["content"]})

        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages_for_ai,
            temperature=0.3,
            max_tokens=200
        )

        return {"reply": completion.choices[0].message.content}
    except Exception as e:
        return {"reply": f"Ошибка связи с ИИ: {str(e)}"}