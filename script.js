let score = 0;
let userName = "";
let chatHistory = []; 
let isAudioMuted = false;
let lastBotText = "";
let currentTopic = "";
let currentSubcategory = "";
let currentQuestionIndex = 0; 
let askedQuestions = []; // Массив вопросов текущего блока
const MAX_QUESTIONS_PER_BLOCK = 10;

window.onload = () => {
    const savedName = localStorage.getItem('studentName');
    if (savedName) {
        document.getElementById('username').value = savedName;
    }
};

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
    askedQuestions = []; // Сбрасываем историю при запуске
    loadQuestionFromAI();
}

async function loadQuestionFromAI() {
    const qBox = document.getElementById('question-text');
    const optBox = document.getElementById('options-container');
    const feedback = document.getElementById('feedback');
    const nextBtn = document.getElementById('next-btn');

    feedback.className = "feedback hidden";
    nextBtn.classList.add('hidden');
    
    currentQuestionIndex++;

    if (currentQuestionIndex > MAX_QUESTIONS_PER_BLOCK) {
        qBox.innerText = `🏆 Блок из 10 вопросов пройден! Ты набрал ${score} очков. Молодец, ${userName}!`;
        optBox.innerHTML = "";
        nextBtn.innerText = "🔄 Начать новый блок из 10 вопросов";
        nextBtn.onclick = () => {
            currentQuestionIndex = 0;
            askedQuestions = []; // Очищаем историю для нового блока
            nextBtn.innerText = "➡️ Следующий вопрос";
            nextBtn.onclick = nextQuestion;
            loadQuestionFromAI();
        };
        nextBtn.classList.remove('hidden');
        return;
    }

    qBox.innerText = `🦉 [Вопрос ${currentQuestionIndex}/${MAX_QUESTIONS_PER_BLOCK}] Профессор Фил придумывает вопрос...`;
    optBox.innerHTML = "";

    try {
        const response = await fetch('/api/get-question', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                name: userName,
                asked_questions: askedQuestions 
            })
        });
        
        const data = await response.json();
        
        if (currentQuestionIndex === 1 && data.user_score !== undefined) {
            score = data.user_score;
            updateScore();
        }
        
        currentTopic = data.topic || "Общие знания";
        currentSubcategory = data.subcategory || "Разное";
        
        // Запоминаем вопрос/подтему в локальную историю
        const fullQuestionSummary = `${currentTopic} (${currentSubcategory}): ${data.question}`;
        askedQuestions.push(fullQuestionSummary);

        qBox.innerText = `[Вопрос ${currentQuestionIndex}/${MAX_QUESTIONS_PER_BLOCK}] ${currentTopic} (${currentSubcategory}): ${data.question}`;
        
        optBox.innerHTML = "";
        data.options.forEach(option => {
            const btn = document.createElement('button');
            btn.className = "option-btn";
            btn.innerText = option;
            btn.onclick = () => checkAnswer(option, data.correctAnswer, data.explanation);
            optBox.appendChild(btn);
        });

    } catch (e) {
        qBox.innerText = "Не удалось загрузить вопрос. Проверь подключение к серверу.";
    }
}

async function checkAnswer(selected, correct, explanation) {
    const feedback = document.getElementById('feedback');
    const optBox = document.getElementById('options-container');
    const nextBtn = document.getElementById('next-btn');

    const cleanSelected = String(selected).trim().toLowerCase();
    const cleanCorrect = String(correct).trim().toLowerCase();
    const isCorrect = (cleanSelected === cleanCorrect);

    Array.from(optBox.children).forEach(btn => btn.disabled = true);

    if (isCorrect) {
        score += 1;
        updateScore();
        feedback.innerText = `✅ Правильно! ${explanation}`;
        feedback.className = "feedback success";
    } else {
        feedback.innerText = `❌ Не совсем так. Правильный ответ: ${correct}. ${explanation}`;
        feedback.className = "feedback error";
    }

    feedback.classList.remove('hidden');
    nextBtn.classList.remove('hidden');

    try {
        await fetch('/api/submit-answer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: userName,
                is_correct: isCorrect,
                topic: currentTopic,
                subcategory: currentSubcategory
            })
        });
    } catch(e) {
        console.log("Ошибка сохранения в базу:", e);
    }
}

function nextQuestion() {
    loadQuestionFromAI();
}

function updateScore() {
    document.getElementById('score').innerText = score;
}

// --- ЧАТ И ГОЛОСОВОЙ ВВОД ---

function renderChatHistory() {
    const chatLog = document.getElementById('chat-log');
    chatLog.innerHTML = "";
    
    chatHistory.forEach((msg, index) => {
        if (msg.role === "user") {
            chatLog.innerHTML += `<div class="msg user-msg"><strong>${userName}:</strong> ${msg.content}</div>`;
        } else {
            const isLastBotMsg = (index === chatHistory.length - 1);
            if (isLastBotMsg) lastBotText = msg.content;
            
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
    if (recognition && micBtn.classList.contains('recording')) {
        micBtn.classList.remove('recording');
        try { recognition.stop(); } catch(e) {}
    }

    const input = document.getElementById('chat-input');
    const text = input.value.trim();
    if (!text) return;
    
    fullSpeechBuffer = "";
    
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

function toggleAudio() {
    isAudioMuted = !isAudioMuted;
    const muteBtn = document.getElementById('mute-btn');
    if (isAudioMuted) {
        muteBtn.innerText = "🔇 Звук выкл";
        muteBtn.classList.add('muted');
        if ('speechSynthesis' in window) window.speechSynthesis.cancel();
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
        const voices = window.speechSynthesis.getVoices();
        const russianVoice = voices.find(voice => voice.lang.includes('ru') || voice.lang.includes('RU'));
        if (russianVoice) utterance.voice = russianVoice;
        window.speechSynthesis.speak(utterance);
    }
}

function repeatLastMessage() {
    if (lastBotText) speakText(lastBotText);
}

// Микрофон
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition;
let fullSpeechBuffer = "";

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
        document.getElementById('chat-input').value = (fullSpeechBuffer + " " + interimText).trim();
    };

    recognition.onend = () => {
        const micBtn = document.getElementById('mic-btn');
        if (micBtn.classList.contains('recording')) {
            try { recognition.start(); } catch (e) {}
        }
    };
}

document.getElementById('mic-btn').addEventListener('click', () => {
    if (!recognition) {
        alert("Твой браузер не поддерживает голосовой ввод. Попробуй Chrome!");
        return;
    }
    const micBtn = document.getElementById('mic-btn');
    const inputField = document.getElementById('chat-input');
    
    if (micBtn.classList.contains('recording')) {
        micBtn.classList.remove('recording');
        try { recognition.stop(); } catch (e) {}
        setTimeout(() => {
            if (inputField.value.trim()) sendMessage();
            fullSpeechBuffer = "";
        }, 100);
    } else {
        fullSpeechBuffer = "";
        inputField.value = "";
        try {
            recognition.start();
            micBtn.classList.add('recording');
        } catch (e) {}
    }
});