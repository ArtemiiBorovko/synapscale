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
    // Если идет запись голоса при нажатии "Отправить", принудительно останавливаем микрофон
    if (recognition && document.getElementById('mic-btn').classList.contains('recording')) {
        recognition.stop();
        return; // onresult подхватит и отправит текст
    }

    const input = document.getElementById('chat-input');
    const text = input.value.trim();
    if (!text) return;
    
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

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition;

if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.lang = 'ru-RU';
    recognition.continuous = true;     // Не выключается автоматически от пауз
    recognition.interimResults = true; // Показывает текст прямо по ходу речи
    
    recognition.onresult = (event) => {
        let finalTranscript = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
            if (event.results[i].isFinal) {
                finalTranscript += event.results[i][0].transcript;
            }
        }
        if (finalTranscript) {
            document.getElementById('chat-input').value = finalTranscript;
        }
    };
    
    recognition.onerror = () => {
        document.getElementById('mic-btn').classList.remove('recording');
    };
    
    recognition.onend = () => {
        document.getElementById('mic-btn').classList.remove('recording');
        // Как только запись остановилась (повторный клик), автоматически отправляем текст
        const inputVal = document.getElementById('chat-input').value.trim();
        if (inputVal) {
            sendMessage();
        }
    };
}

document.getElementById('mic-btn').addEventListener('click', () => {
    if (!recognition) {
        alert("Твой браузер не поддерживает голосовой ввод. Попробуй открыть сайт в Google Chrome!");
        return;
    }
    
    const micBtn = document.getElementById('mic-btn');
    if (micBtn.classList.contains('recording')) {
        recognition.stop(); // Останавливаем вручную, сработает onend и текст уйдет
    } else {
        document.getElementById('chat-input').value = ""; // Очищаем поле перед новой записью
        recognition.start();
        micBtn.classList.add('recording');
    }
});