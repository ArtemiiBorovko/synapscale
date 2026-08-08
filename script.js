const BACKEND_URL = "";

let currentUserName = "";
let currentQuestionData = null;
let chatHistory = [];

// DOM Элементы
const welcomeScreen = document.getElementById("welcome-screen");
const appScreen = document.getElementById("app-screen");
const userNameInput = document.getElementById("user-name");
const startBtn = document.getElementById("start-btn");
const displayName = document.getElementById("display-name");
const scoreDisplay = document.getElementById("score");
const themeToggle = document.getElementById("theme-toggle");

const questionTopic = document.getElementById("question-topic");
const questionText = document.getElementById("question-text");
const optionsContainer = document.getElementById("options-container");
const feedbackContainer = document.getElementById("feedback-container");
const nextBtn = document.getElementById("next-btn");
const speakQuestionBtn = document.getElementById("speak-question-btn");

const chatHistoryDiv = document.getElementById("chat-history");
const chatInput = document.getElementById("chat-input");
const sendBtn = document.getElementById("send-btn");
const voiceBtn = document.getElementById("voice-btn");

window.onload = () => {
    const savedName = localStorage.getItem('studentName');
    if (savedName) {
        userNameInput.value = savedName;
    }
};

// Инициализация темы
function initTheme() {
    const savedTheme = localStorage.getItem("theme") || "dark";
    document.documentElement.setAttribute("data-theme", savedTheme);
}

themeToggle.addEventListener("click", () => {
    const currentTheme = document.documentElement.getAttribute("data-theme");
    const newTheme = currentTheme === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", newTheme);
    localStorage.setItem("theme", newTheme);
});

initTheme();

// Старт приложения
startBtn.addEventListener("click", () => {
    const name = userNameInput.value.trim();
    if (name) {
        currentUserName = name;
        localStorage.setItem('studentName', name);
        displayName.textContent = name;
        welcomeScreen.classList.add("hidden");
        appScreen.classList.remove("hidden");
        loadQuestion();
    }
});

// Загрузка вопроса
async function loadQuestion() {
    questionTopic.textContent = "Анализируем прогресс...";
    questionText.textContent = "ИИ генерирует вопрос...";
    optionsContainer.innerHTML = "";
    feedbackContainer.classList.add("hidden");
    nextBtn.classList.add("hidden");

    try {
        const response = await fetch(`${BACKEND_URL}/api/get-question`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name: currentUserName })
        });
        
        currentQuestionData = await response.json();
        scoreDisplay.textContent = currentQuestionData.user_score;
        
        questionTopic.textContent = `${currentQuestionData.topic} • ${currentQuestionData.subcategory}`;
        questionText.textContent = currentQuestionData.question;

        currentQuestionData.options.forEach(optionText => {
            const btn = document.createElement("button");
            btn.className = "option-btn";
            btn.textContent = optionText;
            btn.onclick = () => handleAnswer(btn, optionText);
            optionsContainer.appendChild(btn);
        });
    } catch (error) {
        questionText.textContent = "Ошибка связи с сервером.";
    }
}

// Озвучка вопроса
speakQuestionBtn.addEventListener("click", () => {
    if (currentQuestionData && currentQuestionData.question) {
        speakText(currentQuestionData.question);
    }
});

// Обработка ответа
// Обработка ответа
async function handleAnswer(selectedBtn, selectedText) {
    // Очищаем строки от пробелов и приводим к нижнему регистру для надежности
    const userAns = String(selectedText).trim().toLowerCase();
    const correctAns = String(currentQuestionData.correctAnswer).trim().toLowerCase();
    const isCorrect = userAns === correctAns;
    
    console.log("Сравнение ответов:", { 
        нажато: `"${userAns}"`, 
        правильно: `"${correctAns}"`, 
        итог: isCorrect 
    });

    // Блокируем кнопки
    const allBtns = optionsContainer.querySelectorAll(".option-btn");
    allBtns.forEach(b => b.disabled = true);

    if (isCorrect) {
        selectedBtn.classList.add("correct");
        feedbackContainer.textContent = `Правильно! ${currentQuestionData.explanation}`;
        feedbackContainer.className = "feedback success";
    } else {
        selectedBtn.classList.add("wrong");
        feedbackContainer.textContent = `Не совсем. Правильный ответ: ${currentQuestionData.correctAnswer}. ${currentQuestionData.explanation}`;
        feedbackContainer.className = "feedback error";
        
        // Подсвечиваем правильный вариант
        allBtns.forEach(b => {
            if (b.textContent.trim().toLowerCase() === correctAns) {
                b.classList.add("correct");
            }
        });
    }

    feedbackContainer.classList.remove("hidden");
    nextBtn.classList.remove("hidden");

    // Отправляем результат на бэкенд
    try {
        const res = await fetch(`${BACKEND_URL}/api/submit-answer`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                name: currentUserName,
                is_correct: isCorrect,
                topic: currentQuestionData.topic,
                subcategory: currentQuestionData.subcategory
            })
        });
        const data = await res.json();
        console.log("Ответ сервера на сохранение очков:", data);
        
        const newScore = data.score !== undefined ? data.score : data.user_score;
        if (newScore !== undefined) {
            scoreDisplay.textContent = newScore;
        }
    } catch (e) {
        console.error("Ошибка сохранения:", e);
    }
}

nextBtn.addEventListener("click", loadQuestion);

// Чат с ИИ
sendBtn.addEventListener("click", sendMessage);
chatInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter") sendMessage();
});

async function sendMessage() {
    const text = chatInput.value.trim();
    if (!text) return;

    appendMessage(text, "user");
    chatInput.value = "";
    chatHistory.push({ role: "user", content: text });

    const aiMsgDiv = appendMessage("Печатает...", "ai");

    try {
        const response = await fetch(`${BACKEND_URL}/api/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name: currentUserName, history: chatHistory })
        });
        const data = await response.json();
        
        aiMsgDiv.innerHTML = data.reply;
        
        // Добавляем кнопку озвучки ответа ИИ
        const speakBtn = document.createElement("button");
        speakBtn.className = "speak-btn";
        speakBtn.innerHTML = `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path></svg>`;
        speakBtn.onclick = () => speakText(data.reply);
        aiMsgDiv.appendChild(speakBtn);

        chatHistory.push({ role: "assistant", content: data.reply });
    } catch (error) {
        aiMsgDiv.textContent = "Ошибка связи.";
    }
}

function appendMessage(text, sender) {
    const div = document.createElement("div");
    div.className = `chat-message ${sender}`;
    div.textContent = text;
    chatHistoryDiv.appendChild(div);
    chatHistoryDiv.scrollTop = chatHistoryDiv.scrollHeight;
    return div;
}

// Web Speech API (Распознавание)
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
if (SpeechRecognition) {
    const recognition = new SpeechRecognition();
    recognition.lang = 'ru-RU';
    
    voiceBtn.addEventListener("click", () => {
        voiceBtn.style.color = "var(--danger)";
        recognition.start();
    });

    recognition.onresult = (event) => {
        chatInput.value = event.results[0][0].transcript;
        voiceBtn.style.color = "";
        sendMessage();
    };

    recognition.onerror = () => {
        voiceBtn.style.color = "";
    };
} else {
    voiceBtn.style.display = "none";
}

// Озвучка текста без эмодзи (Синтез)
function speakText(text) {
    if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel(); // Остановить предыдущую озвучку
        
        // Убираем эмодзи из текста перед озвучкой, чтобы голос их не читал
        const cleanText = text.replace(/[\u{1F000}-\u{1FAFF}]|[\u{2600}-\u{27BF}]/gu, "").trim();
        
        const utterance = new SpeechSynthesisUtterance(cleanText);
        utterance.lang = 'ru-RU';
        utterance.rate = 0.9; // Чуть медленнее для ребенка
        window.speechSynthesis.speak(utterance);
    }
}