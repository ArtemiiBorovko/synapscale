// --- ЛОГИКА ГОЛОСОВОГО ВВОДА И ЧАТА ---

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition;

if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.lang = 'ru-RU'; // Устанавливаем русский язык
    recognition.continuous = false; // Останавливается, когда человек делает паузу
    
    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        // Записываем распознанный текст в поле ввода
        document.getElementById('chat-input').value = transcript;
        document.getElementById('mic-btn').classList.remove('recording');
    };
    
    recognition.onerror = (event) => {
        console.error("Ошибка микрофона:", event.error);
        document.getElementById('mic-btn').classList.remove('recording');
    };
    
    recognition.onend = () => {
        document.getElementById('mic-btn').classList.remove('recording');
    };
}

// Обработчик кнопки микрофона
document.getElementById('mic-btn').addEventListener('click', () => {
    if (!recognition) {
        alert("Твой браузер не поддерживает голосовой ввод. Попробуй открыть сайт в Chrome или Safari!");
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

// Функция отправки текста на сервер
async function sendMessage() {
    const input = document.getElementById('chat-input');
    const text = input.value.trim();
    if (!text) return;
    
    const chatLog = document.getElementById('chat-log');
    
    // Показываем сообщение пользователя
    chatLog.innerHTML += `<div class="msg user-msg"><strong>${userName}:</strong> ${text}</div>`;
    input.value = "";
    
    // Прокручиваем чат вниз
    chatLog.scrollTop = chatLog.scrollHeight;
    
    try {
        // Отправляем запрос на наш сервер в bot.py
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: text, name: userName })
        });
        
        const data = await response.json();
        
        // Показываем ответ робота
        chatLog.innerHTML += `<div class="msg bot-msg"><strong>Фил:</strong> ${data.reply}</div>`;
        chatLog.scrollTop = chatLog.scrollHeight;
    } catch (e) {
        chatLog.innerHTML += `<div class="msg error-msg">Произошла ошибка связи с сервером!</div>`;
    }
}
