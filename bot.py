import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Весь наш интерфейс (HTML, CSS и логика JS) хранится в одной переменной
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Дашборд Детективов</title>
    <style>
        body {
            font-family: 'Comic Sans MS', 'Nunito', sans-serif;
            background-color: #f0f8ff;
            color: #333;
            text-align: center;
            margin: 0;
            padding: 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        h1 {
            color: #ff6b6b;
            font-size: 2.5em;
            text-shadow: 2px 2px #ffe66d;
        }
        .dashboard {
            background: white;
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 10px 20px rgba(0,0,0,0.1);
            max-width: 600px;
            width: 100%;
            border: 4px solid #4ecdc4;
        }
        .profile-selector {
            margin-bottom: 20px;
        }
        button.profile-btn {
            background-color: #4ecdc4;
            color: white;
            border: none;
            padding: 10px 20px;
            font-size: 1.2em;
            border-radius: 15px;
            cursor: pointer;
            margin: 5px;
            transition: transform 0.2s;
        }
        button.profile-btn:hover {
            transform: scale(1.1);
        }
        .mission {
            background-color: #ffe66d;
            padding: 15px;
            border-radius: 15px;
            margin: 20px 0;
            font-size: 1.2em;
        }
        .clicker-btn {
            background-color: #ff6b6b;
            color: white;
            border: none;
            padding: 20px 40px;
            font-size: 1.5em;
            border-radius: 25px;
            cursor: pointer;
            box-shadow: 0 5px 0 #c44536;
            transition: all 0.1s;
            margin: 20px 0;
        }
        .clicker-btn:active {
            transform: translateY(5px);
            box-shadow: 0 0 0 #c44536;
        }
        .progress-container {
            width: 100%;
            background-color: #eee;
            border-radius: 20px;
            height: 30px;
            margin-top: 20px;
            overflow: hidden;
            border: 2px solid #ccc;
        }
        .progress-bar {
            width: 0%;
            height: 100%;
            background-color: #4ecdc4;
            transition: width 0.3s ease;
        }
        #status {
            font-size: 1.3em;
            font-weight: bold;
            margin-top: 15px;
            color: #4ecdc4;
        }
    </style>
</head>
<body>
    <h1>🔍 Дашборд Юных Детективов</h1>
    
    <div class="dashboard">
        <div class="profile-selector">
            <p>Выбери детектива:</p>
            <button class="profile-btn" onclick="setProfile('Николь')">Николь</button>
            <button class="profile-btn" onclick="setProfile('Мия')">Мия</button>
        </div>
        
        <h2 id="welcome-message">Привет! Выбери имя, чтобы начать.</h2>
        
        <div class="mission" id="mission-box" style="display: none;">
            <strong>Текущее дело:</strong> Помочь Антигуа проанализировать данные! Он не может найти ошибку в системе, давай соберем для него подсказки!
        </div>
        
        <button class="clicker-btn" id="click-btn" style="display: none;" onclick="addProgress()">
            🔎 Искать подсказку!
        </button>
        
        <div class="progress-container" id="progress-container" style="display: none;">
            <div class="progress-bar" id="progress-bar"></div>
        </div>
        
        <div id="status"></div>
    </div>

    <script>
        let progress = 0;
        let currentPlayer = "";

        function setProfile(name) {
            currentPlayer = name;
            progress = 0;
            updateUI();
            
            document.getElementById('welcome-message').innerText = `Детектив ${name} готова к делу!`;
            document.getElementById('mission-box').style.display = 'block';
            document.getElementById('click-btn').style.display = 'inline-block';
            document.getElementById('progress-container').style.display = 'block';
            document.getElementById('status').innerText = "Собрано подсказок: 0%";
        }

        function addProgress() {
            if (progress < 100) {
                // Маленький бонус для динамики кликов
                let step = (currentPlayer === 'Мия') ? 15 : 10; 
                progress += step;
                if (progress > 100) progress = 100;
                updateUI();
            }
        }

        function updateUI() {
            document.getElementById('progress-bar').style.width = progress + '%';
            
            if (progress < 100) {
                document.getElementById('status').innerText = `Собрано подсказок: ${progress}%`;
            } else {
                document.getElementById('status').innerText = `Ура, ${currentPlayer}! Ошибка найдена, Антигуа спасен! 🎉`;
                document.getElementById('status').style.color = '#ff6b6b';
                document.getElementById('click-btn').style.display = 'none';
            }
        }
    </script>
</body>
</html>
"""

# При заходе на главную страницу (корневой URL) сервер возвращает наш HTML
@app.get("/", response_class=HTMLResponse)
def read_root():
    return HTML_CONTENT

@app.get("/api/health")
def health_check():
    return {"status": "healthy"}
