import os
import io
import re
import torch
import torchaudio
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, StreamingResponse
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

# Загружаем модель Silero TTS
device = torch.device('cpu')
torch.set_num_threads(4) # Оптимизация для CPU
model, example_text = torch.hub.load(
    repo_or_dir='snakers4/silero-models',
    model='silero_tts',
    language='ru',
    speaker='v4_ru',
    trust_repo=True,
    skip_validation=True
)
model.to(device)

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

        system_prompt = (
            f"Ты — профессор Фил, добрая, умная и веселая сова-наставник. "
            f"Твой собеседник — ребенок по имени {user_name}. "
            f"Отвечай коротко (1-3 предложения), тепло, поддерживающе. "
            f"Объясняй сложные вещи простыми словами. Задавай наводящие вопросы."
        )

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

@app.post("/api/speak")
async def generate_speech(request: Request):
    """Эндпоинт для генерации голоса"""
    data = await request.json()
    text = data.get("text", "")
    
    # Очищаем текст от смайликов и спецсимволов Markdown, 
    # иначе Silero выдаст ошибку
    text = re.sub(r'[\U00010000-\U0010ffff]', '', text)
    text = text.replace('*', '').replace('#', '').strip()
    
    if not text:
        return {"error": "Empty text"}
        
    sample_rate = 48000
    speaker = 'aidar' # Отличный, теплый мужской голос
    
    try:
        # Генерируем аудио-тензор
        audio_tensor = model.apply_tts(
            text=text,
            speaker=speaker,
            sample_rate=sample_rate
        )
        
        # Сохраняем тензор в байтовый буфер как WAV файл
        buffer = io.BytesIO()
        torchaudio.save(buffer, audio_tensor.unsqueeze(0), sample_rate, format="wav")
        buffer.seek(0)
        
        return StreamingResponse(buffer, media_type="audio/wav")
    except Exception as e:
        print(f"TTS Error: {e}")
        return {"error": str(e)}