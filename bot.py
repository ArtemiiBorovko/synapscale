import os
import json
import requests
import pytz
from groq import Groq
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
import pypdf
import docx2txt

from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi import Depends, HTTPException, status
import secrets

# Работа с PostgreSQL
from sqlalchemy import create_engine, text

# Веб-сервер и работа с файлами
from fastapi import FastAPI, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

# 1. ТОКЕНЫ И НАСТРОЙКА (Безопасное чтение из переменных окружения)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
RENDER_APP_URL = os.getenv("RENDER_EXTERNAL_URL", "https://ruleguard-backend.onrender.com")

# Простая проверка на старте
if not all([GROQ_API_KEY, DATABASE_URL, TAVILY_API_KEY]):
    print("⚠️ ВНИМАНИЕ: Не все переменные окружения настроены на сервере!")

groq_client = Groq(api_key=GROQ_API_KEY)
engine = create_engine(DATABASE_URL)
app = FastAPI()

security = HTTPBasic()

def get_current_admin(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, "artemiiborovko")
    correct_password = secrets.compare_digest(credentials.password, "N5oXxMAhdw")
    
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. РАБОТА С БАЗОЙ ДАННЫХ
def init_db():
    with engine.begin() as conn:
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY, 
                user_name TEXT, 
                business_description TEXT, 
                push_time TEXT DEFAULT '09:00',
                push_frequency TEXT DEFAULT 'daily',
                push_days TEXT DEFAULT 'everyday',
                country TEXT,
                location TEXT,
                legal_form TEXT,
                tax_system TEXT,
                employee_count INT,
                has_ip_rights BOOLEAN,
                online_sales BOOLEAN,
                annual_turnover_bracket TEXT,
                main_risk_zones TEXT,
                timezone TEXT DEFAULT 'UTC',
                last_push_date DATE,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        '''))
        
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS reports (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                input_text TEXT,
                report_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        '''))
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS chat_history (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                role TEXT, 
                message_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        '''))
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS tavily_cache (
                id SERIAL PRIMARY KEY,
                query_hash TEXT UNIQUE,
                search_result TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        '''))

    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS push_frequency TEXT DEFAULT 'daily';"))
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS push_days TEXT DEFAULT 'everyday';"))
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS tax_system TEXT;"))
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS employee_count INT;"))
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS has_ip_rights BOOLEAN;"))
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS online_sales BOOLEAN;"))
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS annual_turnover_bracket TEXT;"))
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS main_risk_zones TEXT;"))
    except Exception:
        pass

def save_user_data_extended(user_id, username=None, business=None, country=None, location=None, legal_form=None, push_time=None, timezone=None, tax_system=None, employee_count=None, has_ip_rights=None, online_sales=None, annual_turnover_bracket=None, main_risk_zones=None, push_frequency=None, push_days=None):
    with engine.begin() as conn:
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS push_frequency TEXT DEFAULT 'daily';"))
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS push_days TEXT DEFAULT 'everyday';"))
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS tax_system TEXT;"))
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS employee_count INT;"))
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS has_ip_rights BOOLEAN;"))
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS online_sales BOOLEAN;"))
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS annual_turnover_bracket TEXT;"))
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS main_risk_zones TEXT;"))
        except Exception:
            pass

        result = conn.execute(text("""
            SELECT user_name, business_description, country, location, legal_form, 
                   push_time, timezone, tax_system, employee_count, has_ip_rights, 
                   online_sales, annual_turnover_bracket, main_risk_zones, 
                   push_frequency, push_days 
            FROM users WHERE user_id = :user_id
        """), {"user_id": user_id})
        row = result.fetchone()
        
        if isinstance(push_days, list):
            formatted_push_days = ",".join(push_days)
        else:
            formatted_push_days = push_days

        c_risks = json.dumps(main_risk_zones) if isinstance(main_risk_zones, list) else main_risk_zones

        if row:
            c_name = username if username is not None else row[0]
            c_bus = business if business is not None else row[1]
            c_country = country if country is not None else row[2]
            c_loc = location if location is not None else row[3]
            c_form = legal_form if legal_form is not None else row[4]
            c_push = push_time if push_time is not None else row[5]
            c_tz = timezone if timezone is not None else (row[6] if row[6] else 'UTC')
            c_tax = tax_system if tax_system is not None else row[7]
            c_emp = employee_count if employee_count is not None else row[8]
            c_ip = has_ip_rights if has_ip_rights is not None else row[9]
            c_online = online_sales if online_sales is not None else row[10]
            c_turnover = annual_turnover_bracket if annual_turnover_bracket is not None else row[11]
            c_risk_val = c_risks if c_risks is not None else row[12]
            c_freq = push_frequency if push_frequency is not None else (row[13] if row[13] else 'daily')
            c_p_days = formatted_push_days if formatted_push_days is not None else (row[14] if row[14] else 'everyday')
            
            conn.execute(text('''
                UPDATE users 
                SET user_name = :name, business_description = :bus, country = :country, location = :loc, 
                    legal_form = :form, push_time = :push, timezone = :tz, tax_system = :tax, employee_count = :emp, 
                    has_ip_rights = :ip, online_sales = :online, annual_turnover_bracket = :turnover, main_risk_zones = :risks, 
                    push_frequency = :freq, push_days = :p_days,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = :user_id
            '''), {
                "name": c_name, "bus": c_bus, "country": c_country, "loc": c_loc, "form": c_form, 
                "push": c_push, "tz": c_tz, "tax": c_tax, "emp": c_emp, "ip": c_ip, "online": c_online, 
                "turnover": c_turnover, "risks": c_risk_val, "freq": c_freq, "p_days": c_p_days, "user_id": user_id
            })
        else:
            conn.execute(text('''
                INSERT INTO users (
                    user_id, user_name, business_description, country, location, legal_form, 
                    push_time, timezone, tax_system, employee_count, has_ip_rights, 
                    online_sales, annual_turnover_bracket, main_risk_zones, push_frequency, push_days
                ) 
                VALUES (
                    :user_id, :name, :bus, :country, :loc, :form, 
                    :push, :tz, :tax, :emp, :ip, 
                    :online, :turnover, :risks, :freq, :p_days
                )
            '''), {
                "user_id": user_id, 
                "name": username or "Предприниматель", 
                "bus": business or "Не указано", 
                "country": country or "Не указано", 
                "loc": location or "Не указано", 
                "form": legal_form or "Не указано", 
                "push": push_time or '09:00', 
                "tz": timezone or 'UTC',
                "tax": tax_system, 
                "emp": employee_count, 
                "ip": has_ip_rights, 
                "online": online_sales, 
                "turnover": annual_turnover_bracket, 
                "risks": c_risks,
                "freq": push_frequency or 'daily',
                "p_days": formatted_push_days or 'everyday'
            })

def get_user_context(user_id):
    with engine.connect() as conn:
        result = conn.execute(text("SELECT user_name, business_description, country, location, legal_form, tax_system, employee_count, has_ip_rights, online_sales, annual_turnover_bracket, main_risk_zones FROM users WHERE user_id = :user_id"), {"user_id": user_id})
        row = result.fetchone()
    if row: 
        return f"Пользователь: {row[0] or 'Не указано'}. Страна: {row[2] or 'Не указано'}, Регион: {row[3] or 'Не указано'}, ОПФ: {row[4] or 'Не указано'}. Специфика бизнеса: {row[1] or 'Не указано'}. Система налогообложения: {row[5] or 'Не указано'}. Сотрудников: {row[6] or 'Не указано'}. Права на ИС: {row[7]}, Онлайн-продажи: {row[8]}, Оборот: {row[9] or 'Не указано'}. Зоны риска: {row[10] or 'Не указано'}."
    return "Новый пользователь без настроенного профиля."

def save_report_to_archive(user_id, input_text, report_text):
    try:
        with engine.begin() as conn:
            conn.execute(text('''
                INSERT INTO reports (user_id, input_text, report_text)
                VALUES (:user_id, :input_text, :report_text)
            '''), {"user_id": user_id, "input_text": input_text, "report_text": report_text})
    except Exception as e:
        print(f"Ошибка сохранения отчета: {e}")

def save_chat_message(user_id, role, text_msg):
    try:
        with engine.begin() as conn:
            conn.execute(text('''
                INSERT INTO chat_history (user_id, role, message_text)
                VALUES (:user_id, :role, :message_text)
            '''), {"user_id": user_id, "role": role, "message_text": text_msg})
    except Exception as e:
        print(f"Ошибка сохранения сообщения: {e}")

def get_recent_chat_history(user_id, limit=6):
    try:
        with engine.connect() as conn:
            result = conn.execute(text('''
                SELECT role, message_text FROM chat_history 
                WHERE user_id = :user_id 
                ORDER BY created_at DESC LIMIT :limit
            '''), {"user_id": user_id, "limit": limit})
            rows = result.fetchall()
            return [{"role": r[0], "content": r[1]} for r in reversed(rows)]
    except Exception as e:
        print(f"Ошибка получения истории чата: {e}")
        return []

# 3. УМНЫЙ РОУТЕР GROQ
def safe_groq_request(messages, temperature=0.3, max_tokens=None, is_dispatcher=False):
    if is_dispatcher:
        primary_model = "llama-3.1-8b-instant"
        fallback_model = "llama-3.1-8b-instant"
    else:
        primary_model = "llama-3.3-70b-versatile"
        fallback_model = "llama-3.1-8b-instant"
        
    kwargs = {"model": primary_model, "messages": messages, "temperature": temperature}
    if max_tokens: kwargs["max_tokens"] = max_tokens
        
    try:
        completion = groq_client.chat.completions.create(**kwargs)
        return completion.choices[0].message.content
    except Exception as e:
        if "429" in str(e) or "rate_limit" in str(e):
            kwargs["model"] = fallback_model
            completion = groq_client.chat.completions.create(**kwargs)
            return completion.choices[0].message.content
        else:
            raise e

def check_if_search_needed(history, current_input):
    system_prompt = (
        "Ты — технический диспетчер системы RuleGuard. Твоя задача — определить, "
        "нужен ли глубокий поиск в актуальном интернете (Tavily API) для ответа на вопрос.\n"
        "Ответь строго ОДНИМ словом: 'SEARCH', если пользователь просит найти новые законы, "
        "актуальные штрафы, свежие новости по локации.\n"
        "Ответь строго ОДНИМ словом: 'DIALOG', если вопрос — это уточнение прошлого отчета, "
        "обычное рассуждение, приветствие или продолжение текущей беседы."
    )
    try:
        messages = [{"role": "system", "content": system_prompt}]
        for msg in history[-2:]: 
            messages.append(msg)
        messages.append({"role": "user", "content": f"Вопрос пользователя: {current_input}"})
        
        decision = safe_groq_request(messages, temperature=0.0, max_tokens=5, is_dispatcher=True)
        return "SEARCH" in decision.strip().upper()
    except Exception:
        return True

def parse_and_apply_ai_intent(user_id, text_input):
    system_prompt = (
        "Ты — анализатор намерений пользователя в приложении RuleGuard.\n"
        "Проанализируй текст и выдели настройки расписания или интерфейса, если они есть:\n"
        "1. Тема интерфейса: 'light' или 'dark'. Иначе null.\n"
        "2. Время пушей: найди время в формате HH:MM. Иначе null.\n"
        "3. Частота и дни рассылки:\n"
        "   - Если 'каждый день' или 'ежедневно', верни push_frequency: 'daily', push_days: 'everyday'.\n"
        "   - Если указаны конкретные дни, верни push_frequency: 'custom', push_days: список дней через запятую (mon, tue, wed, thu, fri, sat, sun).\n"
        "   - Если 'раз в месяц', верни push_frequency: 'monthly', push_days: 'monthly'.\n\n"
        "Верни результат СТРОГО в формате JSON без лишнего текста:\n"
        "{\n"
        "  \"action\": \"settings_updated\" или \"none\",\n"
        "  \"theme\": \"light\" или \"dark\" или null,\n"
        "  \"push_time\": \"HH:MM\" или null,\n"
        "  \"push_frequency\": \"daily\", \"custom\", \"monthly\" или null,\n"
        "  \"push_days\": \"...\" или null\n"
        "}"
    )
    try:
        response = safe_groq_request(
            [{"role": "system", "content": system_prompt}, {"role": "user", "content": text_input}],
            temperature=0.0, max_tokens=200, is_dispatcher=True
        )
        cleaned = response.strip()
        if cleaned.startswith("```json"): cleaned = cleaned[7:]
        if cleaned.endswith("```"): cleaned = cleaned[:-3]
        data = json.loads(cleaned.strip())
        
        action = data.get("action", "none")
        if action == "settings_updated":
            theme = data.get("theme")
            push_time = data.get("push_time")
            push_frequency = data.get("push_frequency")
            push_days = data.get("push_days")
            
            with engine.begin() as conn:
                if push_time:
                    conn.execute(text("UPDATE users SET push_time = :pt WHERE user_id = :uid"), {"pt": push_time, "uid": user_id})
                if push_frequency:
                    pd = push_days if push_days is not None else ""
                    conn.execute(text("UPDATE users SET push_frequency = :pf, push_days = :pd WHERE user_id = :uid"), {"pf": push_frequency, "pd": pd, "uid": user_id})

            return {
                "action": action,
                "updated_fields": {"theme": theme, "push_time": push_time, "push_frequency": push_frequency, "push_days": push_days}
            }
    except Exception as e:
        print(f"⚠️ Ошибка парсинга интента: {e}")
    
    return {"action": "none", "updated_fields": {}}

# 4. ПОИСК В ИНТЕРНЕТЕ
def search_internet(query):
    clean_query = query.lower()
    for trash in ["новый пользователь без настроенного профиля.", "вопрос:", "юридические риски штрафы законы актуальное"]:
        clean_query = clean_query.replace(trash, "")
    for char in [".", ",", ";", ":", "!", "?", "-", "_"]:
        clean_query = clean_query.replace(char, " ")
    clean_query = " ".join(clean_query.split()).strip()
    
    if len(clean_query) < 4: return "Недостаточно данных для интернет-поиска."

    try:
        with engine.connect() as conn:
            res = conn.execute(text('''
                SELECT search_result FROM tavily_cache 
                WHERE query_hash = :q AND created_at > CURRENT_TIMESTAMP - INTERVAL '30 minutes'
            '''), {"q": clean_query})
            row = res.fetchone()
            if row: return row[0]
    except Exception:
        pass

    try:
        payload = {"api_key": TAVILY_API_KEY, "query": clean_query, "search_depth": "basic", "max_results": 3}
        headers = {"Content-Type": "application/json"}
        response = requests.post("https://api.tavily.com/search", json=payload, headers=headers, timeout=15)
        
        if response.status_code == 200:
            results = response.json().get("results", [])
            if results:
                context = "\n".join([f"Источник: {r['url']}\nТекст: {r['content']}" for r in results])
                try:
                    with engine.begin() as conn:
                        conn.execute(text('''
                            INSERT INTO tavily_cache (query_hash, search_result) 
                            VALUES (:q, :res) ON CONFLICT (query_hash) 
                            DO UPDATE SET search_result = :res, created_at = CURRENT_TIMESTAMP
                        '''), {"q": clean_query, "res": context})
                except Exception:
                    pass
                return context
    except Exception:
        pass
    return "Не удалось найти свежие нормативные данные в сети."

# 5. ЯДРО АНАЛИЗА БИЗНЕСА И ДИАЛОГОВ
def generate_report_logic(user_id, current_input_text):
    web_data = search_internet(current_input_text)
    system_instruction = (
        "Ты — профессиональный ИИ-юрист RuleGuard, защищающий бизнес от штрафов и проверок.\n"
        "Сделай глубокий анализ на основе предоставленных данных из сети на текущий момент.\n\n"
        "Твой ответ ДОЛЖЕН строго следовать следующей структуре:\n"
        "### 🔥 Главные юридические риски\n"
        "Выдели 2-3 критических риска. Опиши конкретные штрафы или санкции в цифрах, если они есть.\n\n"
        "### 🛡️ Инструкция по защите (Что проверить)\n"
        "Пошаговые легальные действия для предпринимателя.\n\n"
        "### 📊 Уровень угрозы\n"
        "Напиши одну строчку: Низкий, Средний или Высокий, и кратко обоснуй почему."
    )
    user_memory = get_user_context(user_id)
    full_prompt = f"Контекст профиля: {user_memory}\nАКТУАЛЬНЫЕ ДАННЫЕ СЕТИ:\n{web_data}\n\nВводные данные: {current_input_text}"
    
    bot_response = safe_groq_request([{"role": "system", "content": system_instruction}, {"role": "user", "content": full_prompt}], temperature=0.25)
    save_report_to_archive(user_id, current_input_text, bot_response)
    return bot_response

def get_legal_chat_reply(user_id, current_input_text):
    user_context = get_user_context(user_id)
    history_messages = get_recent_chat_history(user_id, limit=4)
    need_search = check_if_search_needed(history_messages, current_input_text)
    
    web_context = ""
    if need_search:
        with engine.connect() as conn:
            res = conn.execute(text("SELECT country, location FROM users WHERE user_id = :user_id"), {"user_id": user_id})
            row = res.fetchone()
            loc_context = f"{row[0]} {row[1]}" if row else ""
        search_query = f"{loc_context} {current_input_text}".strip()
        web_context = search_internet(search_query)

    current_year = datetime.now().year
    system_instruction = (
        f"Ты — ИИ-юрист RuleGuard. Отвечай на вопросы пользователя в контексте его бизнеса.\n"
        f"Текущий год: {current_year}.\n"
        f"Данные бизнеса клиента: {user_context}\n"
        f"Свежие данные из сети: {web_context}\n\n"
        "Отвечай коротко, по делу, понятным языком."
    )

    messages_payload = [{"role": "system", "content": system_instruction}]
    for msg in history_messages: messages_payload.append(msg)
    messages_payload.append({"role": "user", "content": current_input_text})

    bot_response = safe_groq_request(messages_payload, temperature=0.3)
    save_chat_message(user_id, "user", current_input_text)
    save_chat_message(user_id, "assistant", bot_response)
    return bot_response

# =====================================================================
# СЕРВЕРНЫЕ ЭНДПОИНТЫ (WEBAPP API)
# =====================================================================
@app.get("/")
def read_root():
    return {"status": "online"}

@app.get("/api/chat/history/{user_id}")
async def get_webapp_chat_history(user_id: int):
    try:
        history = get_recent_chat_history(user_id, limit=20)
        formatted = [{"role": m["role"], "message_text": m["content"]} for m in history]
        return {"status": "success", "history": formatted}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/chat/message")
async def handle_webapp_chat_message(request: Request):
    try:
        data = await request.json()
        user_id = int(data.get('user_id'))
        text_msg = data.get('text', '').strip()
        if not text_msg: return {"status": "error", "message": "Empty text"}
        
        intent_result = parse_and_apply_ai_intent(user_id, text_msg)
        reply = get_legal_chat_reply(user_id, text_msg)

        return {
            "status": "success", 
            "reply": reply, 
            "report": reply,
            "action": intent_result.get("action"),
            "updated_fields": intent_result.get("updated_fields")
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/analyze")
async def handle_web_analysis(request: Request):
    try:
        data = await request.json()
        user_id = int(data.get('user_id'))
        username = data.get('username', 'Предприниматель')
        country = data.get('country', None)
        location = data.get('location', None)
        legal_form = data.get('legal_form', None)
        details = data.get('business_details', None)
        push_time = data.get('push_time', None)
        user_tz = data.get('timezone', None)
        tax_system = data.get('tax_system', None)
        employee_count = data.get('employee_count', None)
        has_ip_rights = data.get('has_ip_rights', None)
        online_sales = data.get('online_sales', None)
        annual_turnover_bracket = data.get('annual_turnover_bracket', None)
        main_risk_zones = data.get('main_risk_zones', None)
        push_frequency = data.get('push_frequency', 'daily')
        
        raw_push_days = data.get('push_days', 'everyday')
        push_days_str = ",".join(raw_push_days) if isinstance(raw_push_days, list) else str(raw_push_days)

        save_user_data_extended(
            user_id, username=username, business=details, country=country, location=location, 
            legal_form=legal_form, push_time=push_time, timezone=user_tz, tax_system=tax_system, 
            employee_count=employee_count, has_ip_rights=has_ip_rights, online_sales=online_sales, 
            annual_turnover_bracket=annual_turnover_bracket, main_risk_zones=main_risk_zones,
            push_frequency=push_frequency, push_days=push_days_str
        )
        
        if not details and not location: return {"status": "success"}

        compiled_input = f"{country or ''} {location or ''} {legal_form or ''} {details or ''} Налог: {tax_system or ''}"
        report = generate_report_logic(user_id, compiled_input)
        return {"status": "success", "report": report, "reply": report}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/history/{user_id}")
async def get_user_history(user_id: int, tz: str = "UTC"):
    try:
        with engine.connect() as conn:
            user_res = conn.execute(text("SELECT push_time, timezone, push_frequency, push_days FROM users WHERE user_id = :user_id"), {"user_id": user_id})
            user_row = user_res.fetchone()
            
            push_time = user_row[0] if user_row and user_row[0] else "09:00"
            user_tz_str = user_row[1] if user_row and user_row[1] else "UTC"
            push_frequency = user_row[2] if user_row and user_row[2] else "daily"
            push_days = user_row[3] if user_row and len(user_row) > 3 and user_row[3] is not None else "everyday"
            
            try: tz_obj = pytz.timezone(user_tz_str)
            except: tz_obj = pytz.utc
            
            reports_res = conn.execute(text("SELECT input_text, report_text, created_at FROM reports WHERE user_id = :user_id ORDER BY created_at DESC"), {"user_id": user_id})
            history = []
            for row in reports_res.fetchall():
                utc_dt = row[2]
                if utc_dt.tzinfo is None: utc_dt = pytz.utc.localize(utc_dt)
                history.append({
                    "input_text": row[0],
                    "report_text": row[1],
                    "created_at": utc_dt.astimezone(tz_obj).strftime("%d.%m.%Y %H:%M")
                })
                
        return {"status": "success", "push_time": push_time, "push_frequency": push_frequency, "push_days": push_days, "history": history}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/webapp/analyze-doc")
async def handle_webapp_doc(user_id: int, file: UploadFile = File(...)):
    try:
        file_name = file.filename.lower()
        if not (file_name.endswith('.pdf') or file_name.endswith('.docx')):
            return {"status": "error", "message": "Формат не поддерживается. Только PDF или DOCX."}
            
        content = await file.read()
        local_filename = f"webapp_doc_{user_id}_{file_name}"
        with open(local_filename, 'wb') as f: f.write(content)
            
        text_content = ""
        if file_name.endswith('.pdf'):
            with open(local_filename, 'rb') as f:
                reader = pypdf.PdfReader(f)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text: text_content += page_text + "\n"
        elif file_name.endswith('.docx'):
            text_content = docx2txt.process(local_filename)
            
        if os.path.exists(local_filename): os.remove(local_filename)
        text_content = text_content.strip()
        
        if len(text_content) < 50: return {"status": "error", "message": "Не удалось извлечь текст."}
        if len(text_content) > 30000: text_content = text_content[:30000] + "\n\n...[Текст обрезан]..."

        system_instruction = "Ты — опытный ИИ-юрист RuleGuard. Проведи аудит договора.\nСтруктура:\n### 🔎 Вердикт\n### ⚠️ Риски\n### 🛠️ Что изменить"
        user_context = get_user_context(user_id)
        report = safe_groq_request([
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": f"Контекст: {user_context}\n\nТЕКСТ:\n{text_content}"}
        ], temperature=0.2)
        
        save_chat_message(user_id, "user", f"[Документ: {file.filename}]")
        save_chat_message(user_id, "assistant", report)
        return {"status": "success", "report": report, "reply": report}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/webapp/analyze-voice")
async def handle_webapp_voice(user_id: int, file: UploadFile = File(...)):
    filename = f"webapp_voice_{user_id}.ogg"
    try:
        content = await file.read()
        with open(filename, 'wb') as f: f.write(content)
            
        with open(filename, "rb") as audio_file:
            transcription = groq_client.audio.transcriptions.create(
                file=(filename, audio_file.read()), model="whisper-large-v3", language="ru", response_format="text"
            )
            
        user_text = getattr(transcription, 'text', str(transcription)).strip()
        if not user_text: return {"status": "error", "message": "Не удалось распознать речь."}
            
        parse_and_apply_ai_intent(user_id, user_text)
        reply = get_legal_chat_reply(user_id, user_text)

        return {"status": "success", "user_text": user_text, "reply": reply, "report": reply}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        if os.path.exists(filename):
            try: os.remove(filename)
            except: pass

@app.post("/api/reanalyze/{user_id}")
async def reanalyze(user_id: int):
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT country, location, legal_form, business_description FROM users WHERE user_id=:user_id"), {"user_id": user_id})
            row = result.fetchone()
        if not row: return {"status": "error", "message": "Пользователь не найден"}
        report = generate_report_logic(user_id, f"{row[0]} {row[1]} {row[2]} {row[3]}")
        return {"status": "success", "report": report, "reply": report}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/admin/stats")
def get_admin_stats(admin: str = Depends(get_current_admin)):
    try:
        with engine.connect() as conn:
            total_users = conn.execute(text("SELECT COUNT(*) FROM users")).scalar()
            loc_res = conn.execute(text("SELECT location, COUNT(*) as count FROM users WHERE location IS NOT NULL GROUP BY location ORDER BY count DESC LIMIT 5")).fetchall()
            locations = {"labels": [r[0] for r in loc_res], "data": [r[1] for r in loc_res]}
            
            push_res = conn.execute(text("SELECT push_time, COUNT(*) as count FROM users GROUP BY push_time ORDER BY push_time")).fetchall()
            pushes = {"labels": [r[0] for r in push_res], "data": [r[1] for r in push_res]}
            
            reports_count = conn.execute(text("SELECT COUNT(*) FROM reports")).scalar()
            chat_count = conn.execute(text("SELECT COUNT(*) FROM chat_history WHERE role = 'user'")).scalar()
            groq_requests = {"labels": ["Анализ бизнеса", "Диалоги в чате"], "data": [reports_count, chat_count]}

            users_res = conn.execute(text("""
                SELECT u.user_id, u.user_name, u.country, u.location, u.legal_form, u.business_description, u.push_time, u.timezone,
                       (SELECT COUNT(*) FROM reports r WHERE r.user_id = u.user_id),
                       (SELECT COUNT(*) FROM chat_history c WHERE c.user_id = u.user_id AND c.role = 'user')
                FROM users u
            """)).fetchall()
            
            users_details = [{
                "user_id": r[0], "user_name": r[1] or "Без имени", "country": r[2] or "-", "location": r[3] or "-",
                "legal_form": r[4] or "-", "business_description": r[5] or "-", "push_time": r[6] or "-",
                "timezone": r[7] or "-", "reports_count": r[8], "chat_count": r[9]
            } for r in users_res]

        return {"status": "success", "total_users": total_users, "locations": locations, "pushes": pushes, "groq_requests": groq_requests, "users_details": users_details}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/admin", response_class=HTMLResponse)
def get_admin_dashboard(admin: str = Depends(get_current_admin)):
    return "<!DOCTYPE html><html><head><title>Admin</title></head><body><h1>RuleGuard Admin Panel</h1></body></html>"

init_db()
scheduler = BackgroundScheduler(daemon=True)
scheduler.start()