let currentQuestionIndex = 0;
let score = 0;
let userName = "";

// Восстанавливаем имя из памяти при загрузке страницы
window.onload = () => {
    const savedName = localStorage.getItem('studentName');
    if (savedName) {
        document.getElementById('username').value = savedName;
    }
};

const lessons = [
    {
        type: "iq_logic",
        question: "Какое число будет следующим: 2, 4, 8, 16, ...?",
        image: null,
        options: ["24", "32", "64", "20"],
        correctAnswer: "32",
        explanation: "Каждое следующее число умножается на 2."
    },
    {
        type: "rebus",
        question: "Что здесь зашифровано?",
        image: "👁️ + 🍏", 
        options: ["Груша", "Зрение", "Яблоко", "Глазное яблоко"],
        correctAnswer: "Глазное яблоко",
        explanation: "Глаз + Яблоко = Глазное яблоко."
    },
    {
        type: "visual_logic",
        question: "Какая фигура здесь лишняя?",
        image: "🔺 🔴 🟦 🟢", 
        options: ["Красный треугольник", "Красный круг", "Синий квадрат", "Зеленый круг"],
        correctAnswer: "Красный треугольник",
        explanation: "У треугольника есть острые углы, а остальные фигуры скругленные." 
    }
];

function saveNameAndStart() {
    const nameInput = document.getElementById('username').value.trim();
    if (nameInput === "") {
        alert("Пожалуйста, напиши своё имя, чтобы мы могли начать! 😊");
        return;
    }
    
    userName = nameInput;
    localStorage.setItem('studentName', userName);

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
        feedback.innerText = `✅ Правильно, ${userName}! ${explanation}`;
        feedback.className = "feedback success";
    } else {
        feedback.innerText = `❌ Не совсем так, ${userName}. Правильный ответ: ${correct}. ${explanation}`;
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


// --- РАБОТА С МИКРОФОНОМ И ГОЛОСОМ ---

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
    };
    
    recognition.onerror = () => {
        document.getElementById('mic-btn').classList.remove('recording');
    };
    
    recognition.onend = () => {
        document.getElementById('mic-btn').classList.remove('recording');
    };
}

// Кнопка микрофона
document.getElementById('mic-btn').addEventListener('click', () => {
    if (!recognition) {
        alert("Твой браузер не поддерживает голосовой ввод. Попробуй открыть сайт в Google Chrome!");
        return;
    }
    
    const micBtn = document.getElementById('mic-btn');
    if (micBtn.classList.contains('recording')) {
        recognition.stop();
        micBtn.classList.remove('recording');
    } else {
        recognition.start();
        micBtn.classList.add('recording');
    }
});

// Отправка текста серверу (профессору Филу)
async function sendMessage() {
    const input = document.getElementById('chat-input');
    const text = input.value.trim();
    if (!text) return;
    
    const chatLog = document.getElementById('chat-log');
    
    chatLog.innerHTML += `<div class="msg user-msg"><strong>${userName}:</strong> ${text}</div>`;
    input.value = "";
    chatLog.scrollTop = chatLog.scrollHeight;
    
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: text, name: userName })
        });
        
        const data = await response.json();
        chatLog.innerHTML += `<div class="msg bot-msg"><strong>Фил:</strong> ${data.reply}</div>`;
        chatLog.scrollTop = chatLog.scrollHeight;
    } catch (e) {
        chatLog.innerHTML += `<div class="msg error-msg">Ошибка связи с сервером!</div>`;
    }
}
