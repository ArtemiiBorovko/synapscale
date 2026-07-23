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
    localStorage.setItem('studentName', userName); // Запоминаем имя

    // Прячем приветствие, показываем уроки
    document.getElementById('welcome-screen').classList.add('hidden');
    document.getElementById('main-screen').classList.remove('hidden');
    
    // Фил обращается по имени
    document.getElementById('greeting').innerText = `Вперёд к знаниям, ${userName}! 🚀`;
}

function goBack() {
    // Возвращаемся на стартовый экран
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
        // Передаем ответ на проверку
        btn.onclick = () => checkAnswer(option, currentLesson.correctAnswer, currentLesson.explanation);
        optBox.appendChild(btn);
    });
}

function checkAnswer(selected, correct, explanation) {
    const feedback = document.getElementById('feedback');
    const optBox = document.getElementById('options-container');
    
    // Блокируем кнопки
    Array.from(optBox.children).forEach(btn => btn.disabled = true);

    if (selected === correct) {
        score += 10;
        updateScore();
        // Используем имя при правильном ответе
        feedback.innerText = `✅ Правильно, ${userName}! ${explanation}`;
        feedback.className = "feedback success";
    } else {
        // Мягко поправляем
        feedback.innerText = `❌ Не совсем так, ${userName}. Правильный ответ: ${correct}. ${explanation}`;
        feedback.className = "feedback error";
    }

    // Через 3.5 секунды следующий вопрос
    setTimeout(() => {
        currentQuestionIndex++;
        loadQuestion();
    }, 3500);
}

function updateScore() {
    document.getElementById('score').innerText = score;
}
