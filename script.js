let currentQuestionIndex = 0;
let score = 0;

// Массив с первыми уроками
const lessons = [
    {
        type: "iq_logic",
        question: "Продолжи числовой ряд: 2, 4, 8, 16, ...",
        image: null,
        options: ["24", "32", "64", "20"],
        correctAnswer: "32",
        explanation: "Каждое следующее число умножается на 2."
    },
    {
        type: "rebus",
        question: "Разгадай ребус: 👁️ + 🍏 = ?",
        image: null, // Позже сюда можно вставить реальную ссылку на картинку, например "/static/rebus1.png"
        options: ["Груша", "Зрение", "Яблоко", "Глазное яблоко"],
        correctAnswer: "Глазное яблоко",
        explanation: "Глаз + Яблоко = Глазное яблоко."
    },
    {
        type: "visual_logic",
        question: "Какая фигура лишняя?",
        image: "🔺 🔴 🟦 🟢", // Эмуляция картинки
        options: ["Красный треугольник", "Красный круг", "Синий квадрат", "Зеленый круг"],
        correctAnswer: "Красный треугольник",
        explanation: "Треугольник имеет углы, остальные фигуры в этом ряду (если бы они были нарисованы) скругленные или симметричные иначе." // Пример логики
    }
];

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
    
    // Прячем старый фидбек
    feedback.className = "feedback hidden";
    
    if (currentQuestionIndex >= lessons.length) {
        qBox.innerText = "Уроки завершены! Ты молодец!";
        imgBox.innerHTML = "";
        optBox.innerHTML = "";
        return;
    }

    const currentLesson = lessons[currentQuestionIndex];
    qBox.innerText = currentLesson.question;
    
    // Если есть картинка, показываем
    if (currentLesson.image) {
        imgBox.innerHTML = `<div class="placeholder-img">${currentLesson.image}</div>`;
    } else {
        imgBox.innerHTML = "";
    }

    // Генерируем кнопки с ответами
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
    
    // Блокируем кнопки после ответа
    Array.from(optBox.children).forEach(btn => btn.disabled = true);

    if (selected === correct) {
        score += 10;
        updateScore();
        feedback.innerText = "✅ Правильно! " + explanation;
        feedback.className = "feedback success";
    } else {
        feedback.innerText = "❌ Ошибка. Правильный ответ: " + correct + ". " + explanation;
        feedback.className = "feedback error";
    }

    // Переход к следующему вопросу через 3 секунды
    setTimeout(() => {
        currentQuestionIndex++;
        loadQuestion();
    }, 3000);
}

function updateScore() {
    document.getElementById('score').innerText = score;
}
