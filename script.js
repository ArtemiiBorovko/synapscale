let currentQuestionIndex = 0;
let score = 0;
let userName = "";
let chatHistory = []; 
let isAudioMuted = false;
let lastBotText = "";

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
    const nextBtn = document.getElementById('next-btn'); // Находим новую кнопку

    // Блокируем кнопки после ответа[cite: 9]
    Array.from(optBox.children).forEach(btn => btn.disabled = true);

    if (selected === correct) {
        score += 1; // Начисляем 1 очко вместо 10[cite: 9]
        updateScore(); //[cite: 9]
        feedback.innerText = `✅ Правильно! ${explanation}`; //[cite: 9]
        feedback.className = "feedback success"; //[cite: 9]
    } else {
        feedback.innerText = `❌ Не совсем так. Правильный ответ: ${correct}. ${explanation}`; //[cite: 9]
        feedback.className = "feedback error"; //[cite: 9]
    }

    feedback.classList.remove('hidden');
    nextBtn.classList.remove('hidden'); // Показываем кнопку перехода
    // setTimeout убран — теперь ждем нажатия кнопки[cite: 9]
}

// Новая функция для перелистывания
function nextQuestion() {
    document.getElementById('next-btn').classList.add('hidden');
    currentQuestionIndex++;
    loadQuestion();
}

function updateScore() {
    document.getElementById('score').innerText = score;
}

// --- ЧАТ И ПАМЯТЬ ---

function renderChatHistory() {
    const chatLog = document.getElementById('chat-log');
    chatLog.innerHTML = "";
    
    chatHistory.forEach((msg, index) => {
        if (msg.role === "user") {
            chatLog.innerHTML += `<div class="msg user-msg"><strong>${userName}:</strong> ${msg.content}</div>`;
        } else {
            const isLastBotMsg = (index === chatHistory.length - 1);
            if (isLastBotMsg) {
                lastBotText = msg.content;
            }
            
            let repeatButtonHtml = isLastBotMsg ? ` <button class="repeat-btn" onclick="repeatLastMessage()">🔊 Повторить</button>` : '';
            
            chatLog.innerHTML += `
                <div class="msg bot-msg">
                    <strong>Фил:</strong> ${msg.content}
                    ${repeatButtonHtml}
                </div>`;
        }
    });
    chatLog.scrollTop = chatLog.scrollHeight;
}

async function sendMessage() {
    const micBtn = document.getElementById('mic-btn');
    
    // Если при нажатии "Отправить" микрофон всё ещё пишет, корректно его выключаем
    if (recognition && micBtn.classList.contains('recording')) {
        micBtn.classList.remove('recording');
        try { recognition.stop(); } catch(e) {}
    }

    const input = document.getElementById('chat-input');
    const text = input.value.trim();
    if (!text) return;
    
    fullSpeechBuffer = ""; // Очищаем буфер рации
    
    chatHistory.push({ role: "user", content: text });
    localStorage.setItem('chatHistory_' + userName, JSON.stringify(chatHistory));
    
    renderChatHistory();
    input.value = "";
    
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ history: chatHistory, name: userName })
        });
        
        const data = await response.json();
        
        chatHistory.push({ role: "assistant", content: data.reply });
        lastBotText = data.reply;
        localStorage.setItem('chatHistory_' + userName, JSON.stringify(chatHistory));
        
        renderChatHistory();
        speakText(data.reply); 
        
    } catch (e) {
        const chatLog = document.getElementById('chat-log');
        chatLog.innerHTML += `<div class="msg error-msg">Ошибка связи с сервером!</div>`;
    }
}

// --- УПРАВЛЕНИЕ ЗВУКОМ И ПОВТОР ---

function toggleAudio() {
    isAudioMuted = !isAudioMuted;
    const muteBtn = document.getElementById('mute-btn');
    
    if (isAudioMuted) {
        muteBtn.innerText = "🔇 Звук выкл";
        muteBtn.classList.add('muted');
        if ('speechSynthesis' in window) {
            window.speechSynthesis.cancel();
        }
    } else {
        muteBtn.innerText = "🔊 Звук вкл";
        muteBtn.classList.remove('muted');
    }
}

function speakText(text) {
    if (isAudioMuted) return; 
    
    if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel(); 

        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = 'ru-RU';
        utterance.rate = 1.0; 
        utterance.pitch = 1.0;

        const voices = window.speechSynthesis.getVoices();
        const russianVoice = voices.find(voice => voice.lang.includes('ru') || voice.lang.includes('RU'));
        if (russianVoice) {
            utterance.voice = russianVoice;
        }

        window.speechSynthesis.speak(utterance);
    }
}

function repeatLastMessage() {
    if (lastBotText) {
        speakText(lastBotText);
    }
}

if ('speechSynthesis' in window) {
    window.speechSynthesis.onvoiceschanged = () => {
        window.speechSynthesis.getVoices();
    };
}

// --- МИКРОФОН (Непрерывный режим до повторного нажатия) ---

// --- МИКРОФОН (Режим рации: пишем всё в буфер до повторного нажатия) ---

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition;
let fullSpeechBuffer = ""; // Накопительный буфер для всей речи

if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.lang = 'ru-RU';
    recognition.continuous = true;
    recognition.interimResults = true;
    
    recognition.onresult = (event) => {
        let interimText = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
            const transcript = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
                fullSpeechBuffer += " " + transcript;
            } else {
                interimText += transcript;
            }
        }
        // Показываем в инпуте то, что уже точно сказано + текущие промежуточные слова
        document.getElementById('chat-input').value = (fullSpeechBuffer + " " + interimText).trim();
    };
    
    recognition.onerror = (event) => {
        console.log("Ошибка распознавания:", event.error);
    };
    
    recognition.onend = () => {
        const micBtn = document.getElementById('mic-btn');
        // Если браузер сам попытался выключить запись (из-за паузы), а пользователь её не завершал — тут же возобновляем сессию!
        if (micBtn.classList.contains('recording')) {
            try {
                recognition.start();
                return;
            } catch (e) {
                console.log("Перезапуск микрофона:", e);
            }
        }
    };
}

document.getElementById('mic-btn').addEventListener('click', () => {
    if (!recognition) {
        alert("Твой браузер не поддерживает голосовой ввод. Попробуй открыть сайт в Google Chrome!");
        return;
    }
    
    const micBtn = document.getElementById('mic-btn');
    const inputField = document.getElementById('chat-input');
    
    if (micBtn.classList.contains('recording')) {
        // ВТОРОЙ КЛИК: Пользователь закончил говорить и останавливает запись
        micBtn.classList.remove('recording');
        try {
            recognition.stop();
        } catch (e) {}
        
        // Фиксируем итоговый текст из буфера и отправляем
        setTimeout(() => {
            const finalVal = inputField.value.trim();
            if (finalVal) {
                sendMessage();
            }
            fullSpeechBuffer = ""; // Очищаем буфер для следующего раза
        }, 100);
        
    } else {
        // ПЕРВЫЙ КЛИК: Начинаем запись с чистого листа
        fullSpeechBuffer = "";
        inputField.value = "";
        try {
            recognition.start();
            micBtn.classList.add('recording');
        } catch (e) {
            console.log("Ошибка запуска:", e);
        }
    }
});