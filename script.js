const BACKEND_URL = "";

let currentUserName = "";
let currentQuestionData = null;
let chatHistory = [];
let currentQuestionIndex = 0; // Счётчик вопросов в текущем блоке (до 10)
const BLOCK_SIZE = 10;

// DOM Элементы
const welcomeScreen = document.getElementById("welcome-screen");
const appScreen = document.getElementById("app-screen");
const userNameInput = document.getElementById("user-name");
const startBtn = document.getElementById("start-btn");
const displayName = document.getElementById("display-name");
const scoreDisplay = document.getElementById("score");
const themeToggle = document.getElementById("theme-toggle");

const questionTopic = document.getElementById("question-topic");
const questionProgress = document.getElementById("question-progress");
const questionText = document.getElementById("question-text");
const optionsContainer = document.getElementById("options-container");
const feedbackContainer = document.getElementById("feedback-container");
const nextBtn = document.getElementById("next-btn");
const speakQuestionBtn = document.getElementById("speak-question-btn");
const quizCard = document.querySelector(".quiz-card");
const completionCard = document.getElementById("completion-card");
const restartBlockBtn = document.getElementById("restart-block-btn");

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

startBtn.addEventListener("click", () => {
    const name = userNameInput.value.trim();
    if (name) {
        currentUserName = name;
        localStorage.setItem('studentName', name);
        displayName.textContent = name;
        welcomeScreen.classList.add("hidden");
        appScreen.classList.remove("hidden");
        currentQuestionIndex = 0;
        loadQuestion();
    }
});

async function loadQuestion() {
    // Проверка лимита в 10 вопросов на блок
    if (currentQuestionIndex >= BLOCK_SIZE) {
        quizCard.classList.add("hidden");
        completionCard.classList.remove("hidden");
        document.getElementById("completion-stats").textContent = `Вы успешно завершили блок из ${BLOCK_SIZE} вопросов!`;
        return;
    }

    quizCard.classList.remove("hidden");
    completionCard.classList.add("hidden");

    questionTopic.textContent = "Анализируем прогресс...";
    questionProgress.textContent = `Вопрос ${currentQuestionIndex + 1} из ${BLOCK_SIZE}`;
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
        questionProgress.textContent = `Вопрос ${currentQuestionIndex + 1} из ${BLOCK_SIZE}`;
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

restartBlockBtn.addEventListener("click", () => {
    currentQuestionIndex = 0;
    loadQuestion();
});

speakQuestionBtn.addEventListener("click", () => {
    if (currentQuestionData && currentQuestionData.question) {
        speakText(currentQuestionData.question);
    }
});

async function handleAnswer(selectedBtn, selectedText) {
    const userAns = String(selectedText).trim().toLowerCase();
    const correctAns = String(currentQuestionData.correctAnswer).trim().toLowerCase();
    const isCorrect = userAns === correctAns;

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
        
        allBtns.forEach(b => {
            if (b.textContent.trim().toLowerCase() === correctAns) {
                b.classList.add("correct");
            }
        });
    }

    feedbackContainer.classList.remove("hidden");
    nextBtn.classList.remove("hidden");

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
        const newScore = data.score !== undefined ? data.score : data.user_score;
        if (newScore !== undefined) {
            scoreDisplay.textContent = newScore;
        }
    } catch (e) {
        console.error("Ошибка сохранения:", e);
    }
}

nextBtn.addEventListener("click", () => {
    currentQuestionIndex++;
    loadQuestion();
});

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

// Управление микрофоном (запись идет до повторного нажатия кнопки)
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
if (SpeechRecognition) {
    const recognition = new SpeechRecognition();
    recognition.lang = 'ru-RU';
    recognition.continuous = true; // Не прерываться при паузах
    recognition.interimResults = true; // Показывать промежуточные результаты

    let isRecording = false;
    let finalTranscript = '';

    voiceBtn.addEventListener("click", () => {
        if (!isRecording) {
            // Старт записи
            finalTranscript = chatInput.value ? chatInput.value + ' ' : '';
            try {
                recognition.start();
            } catch(e) {}
        } else {
            // Остановка записи вручную
            try {
                recognition.stop();
            } catch(e) {}
        }
    });

    recognition.onstart = () => {
        isRecording = true;
        voiceBtn.classList.add("recording");
    };

    recognition.onresult = (event) => {
        let interim = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
            if (event.results[i].isFinal) {
                finalTranscript += event.results[i][0].transcript + ' ';
            } else {
                interim += event.results[i][0].transcript;
            }
        }
        chatInput.value = (finalTranscript + interim).trim();
    };

    recognition.onerror = () => {
        stopRecordingState();
    };

    recognition.onend = () => {
        stopRecordingState();
    };

    function stopRecordingState() {
        isRecording = false;
        voiceBtn.classList.remove("recording");
    }
} else {
    voiceBtn.style.display = "none";
}

function speakText(text) {
    if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
        const cleanText = text.replace(/[\u{1F000}-\u{1FAFF}]|[\u{2600}-\u{27BF}]/gu, "").trim();
        const utterance = new SpeechSynthesisUtterance(cleanText);
        utterance.lang = 'ru-RU';
        utterance.rate = 0.9;
        window.speechSynthesis.spend = window.speechSynthesis.speak(utterance);
    }
}