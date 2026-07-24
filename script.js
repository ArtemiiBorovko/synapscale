let currentQuestionIndex = 0;
let score = 0;
let userName = "";
let chatHistory = []; // Массив для хранения памяти диалога

// Восстанавливаем имя из памяти при загрузке страницы
window.onload = () => {
    const savedName = localStorage.getItem('studentName');
    if (savedName) {
        document.getElementById('username').value = savedName;
    }
};

const lessons = [
    { type: "iq_logic", question: "Какое число будет следующим: 2, 4, 8, 16, ...?", image: null, options: ["24", "32", "64", "20"], correctAnswer: "32", explanation: "Каждое следующее число умножается на 2." },
    { type: "rebus", question: "Что здесь зашифровано?", image: "👁️ + 🍏", options: ["Груша", "Зрение", "Яблоко", "Глазное яблоко"], correctAnswer: "Глазное яблоко", explanation: "Глаз + Яблоко = Глазное яблоко." },
    { type: "visual_logic", question: "Какая фигура здесь лишняя?", image: "🔺 🔴 🟦 🟢", options: ["Красный треугольник", "Красный круг", "Синий квадрат", "Зеленый круг"], correctAnswer: "Красный треугольник", explanation: "У треугольника есть острые углы, а остальные фигуры скругленные." }
];

function saveNameAndStart() {
    const nameInput = document.getElementById('username').value.trim();
    if (nameInput === "") {
        alert("Пожалуйста, напиши своё имя, чтобы мы могли начать! 😊");
        return;
    }
    
    userName = nameInput;
    localStorage.setItem('studentName', userName);

    // Загружаем историю чата именно для этого пользователя
    chatHistory = JSON.parse(localStorage.getItem('chatHistory_' + userName)) || [];
    renderChatHistory();

    document.getElementById('welcome-screen').classList.add('hidden');
    document.getElementById('main-screen').classList.remove('hidden');
    document.getElementById('greeting').innerText = `Вперёд к знаниям, ${userName}! 🚀`;
}

function goBack() {
    document.getElementById('main-screen').classList.add('hidden');
    document.getElementById('welcome-screen').classList.remove('hidden');
}

function startLesson() {
    document.getElementById('start-btn').style.display = 'none';
    currentQuestionIndex = 0;
    score = 0;
    updateScore();
    loadQuestion();
}

function loadQuestion() {
    const qBox = document.getElementById('question-text');
    const imgBox = document.getElementById('image-container');
    const optBox = document.getElementById('options-container');
    const feedback = document.getElementById('feedback');
    
    feedback.className = "feedback hidden";
    
    if (currentQuestionIndex >= lessons.length) {
        qBox.innerText = `Уроки завершены! Ты просто супер, ${userName}! 🏆`;
        imgBox.innerHTML = "";
        optBox.innerHTML = "";
        return;
    }

    const currentLesson = lessons[currentQuestionIndex];
    qBox.innerText = currentLesson.question;
    
    if (currentLesson.image) {
        imgBox.innerHTML = `<div class="placeholder-img">${currentLesson.image}</div>`;
    } else {
        imgBox.innerHTML = "";
    }

    optBox.innerHTML = "";
    currentLesson.options.forEach(option => {
        const btn = document.createElement('button');
        btn.className = "option-btn";
        btn.innerText = option;
        btn.onclick = () => checkAnswer(option, currentLesson.correctAnswer, currentLesson.explanation);
        optBox.appendChild(btn);
    });
}

function checkAnswer(selected, correct, explanation) {
    const feedback = document.getElementById('feedback');
    const optBox = document.getElementById('options-container');
    
    Array.from(optBox.children).forEach(btn => btn.disabled = true);

    if (selected === correct) {
        score += 10;
        updateScore();
        feedback.innerText = `✅ Правильно! ${explanation}`;
        feedback.className = "feedback success";
    } else {
        feedback.innerText = `❌ Не совсем так. Правильный ответ: ${correct}. ${explanation}`;
        feedback.className = "feedback error";
    }

    setTimeout(() => {
        currentQuestionIndex++;
        loadQuestion();
    }, 3500);
}

function updateScore() {
    document.getElementById('score').innerText = score;
}

// --- ЧАТ И ПАМЯТЬ ---

function renderChatHistory() {
    const chatLog = document.getElementById('chat-log');
    chatLog.innerHTML = "";
    chatHistory.forEach(msg => {
        if (msg.role === "user") {
            chatLog.innerHTML += `<div class="msg user-msg"><strong>${userName}:</strong> ${msg.content}</div>`;
        } else {
            chatLog.innerHTML += `<div class="msg bot-msg"><strong>Фил:</strong> ${msg.content}</div>`;
        }
    });
    chatLog.scrollTop = chatLog.scrollHeight;
}

async function sendMessage() {
    const input = document.getElementById('chat-input');
    const text = input.value.trim();
    if (!text) return;
    
    // Добавляем сообщение пользователя в историю
    chatHistory.push({ role: "user", content: text });
    localStorage.setItem('chatHistory_' + userName, JSON.stringify(chatHistory));
    
    renderChatHistory();
    input.value = "";
    
    try {
        // Отправляем на сервер ВСЮ историю, чтобы ИИ помнил контекст
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ history: chatHistory, name: userName })
        });
        
        const data = await response.json();
        
        // Добавляем ответ бота в историю
        chatHistory.push({ role: "assistant", content: data.reply });
        localStorage.setItem('chatHistory_' + userName, JSON.stringify(chatHistory));
        
        renderChatHistory();
        speakText(data.reply); // Озвучиваем ответ!
        
    } catch (e) {
        const chatLog = document.getElementById('chat-log');
        chatLog.innerHTML += `<div class="msg error-msg">Ошибка связи с сервером!</div>`;
    }
}

// --- ОЗВУЧКА И МИКРОФОН ---

function speakText(text) {
    if ('speechSynthesis' in window) {
        // Очищаем текст от смайликов, чтобы синтезатор их не читал как странные слова
        const cleanText = text.replace(/([\u2700-\u27BF]|[\uE000-\uF8FF]|\uD83C[\uDC00-\uDFFF]|\uD83D[\uDC00-\uDFFF]|[\u2011-\u26FF]|\uD83E[\uDD10-\uDDFF])/g, '');
        
        const utterance = new SpeechSynthesisUtterance(cleanText);
        utterance.lang = 'ru-RU';
        utterance.rate = 0.9;  // Делаем речь чуть медленнее (1.0 это норма)
        utterance.pitch = 1.2; // Делаем голос чуть выше, чтобы звучал добрее
        
        window.speechSynthesis.speak(utterance);
    }
}

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition;

if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.lang = 'ru-RU';
    recognition.continuous = false;
    
    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        document.getElementById('chat-input').value = transcript;
        document.getElementById('mic-btn').classList.remove('recording');
        sendMessage(); // Автоматически отправляем после диктовки
    };
    
    recognition.onerror = () => document.getElementById('mic-btn').classList.remove('recording');
    recognition.onend = () => document.getElementById('mic-btn').classList.remove('recording');
}

document.getElementById('mic-btn').addEventListener('click', () => {
    if (!recognition) {
        alert("Твой браузер не поддерживает голосовой ввод. Попробуй открыть сайт в Google Chrome!");
        return;
    }
    
    const micBtn = document.getElementById('mic-btn');
    if (micBtn.classList.contains('recording')) {
        recognition.stop();
    } else {
        recognition.start();
        micBtn.classList.add('recording');
    }
});
