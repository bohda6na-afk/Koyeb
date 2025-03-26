// Функціональність свайпів для профілів
document.addEventListener('DOMContentLoaded', function() {
    // Ініціалізація функціональності свайпів
    initSwipeCards();
    
    // Ініціалізація чату (якщо потрібно)
    initChat();
});

// Ініціалізація карток для свайпів
function initSwipeCards() {
    const profileCards = document.querySelectorAll('.swipe-card');
    
    if (profileCards.length === 0) return;
    
    // Поточна картка
    let currentCardIndex = 0;
    let currentCard = profileCards[currentCardIndex];
    
    // Показати першу картку
    if (currentCard) {
        currentCard.classList.add('active');
    }
    
    // Кнопки лайка і дизлайка
    const likeButton = document.querySelector('.like-button');
    const dislikeButton = document.querySelector('.dislike-button');
    
    if (likeButton) {
        likeButton.addEventListener('click', function() {
            likeProfile(currentCard.dataset.profileId);
            showNextCard();
        });
    }
    
    if (dislikeButton) {
        dislikeButton.addEventListener('click', function() {
            dislikeProfile(currentCard.dataset.profileId);
            showNextCard();
        });
    }
    
    // Показати наступну картку
    function showNextCard() {
        if (currentCard) {
            // Анімація свайпу вправо або вліво
            currentCard.classList.add('swiped');
            currentCard.classList.remove('active');
            
            // Показати наступну картку через деякий час (після анімації)
            setTimeout(() => {
                currentCardIndex++;
                
                // Перевірка, чи є ще картки
                if (currentCardIndex < profileCards.length) {
                    currentCard = profileCards[currentCardIndex];
                    currentCard.classList.add('active');
                } else {
                    // Більше немає карток, показати повідомлення або перезавантажити
                    showNoMoreProfiles();
                }
            }, 300); // Час анімації свайпу
        }
    }
    
    // Додавання підтримки жестів свайпу для мобільних пристроїв
    let touchStartX = 0;
    let touchEndX = 0;
    
    document.addEventListener('touchstart', function(e) {
        touchStartX = e.changedTouches[0].screenX;
    });
    
    document.addEventListener('touchend', function(e) {
        touchEndX = e.changedTouches[0].screenX;
        handleSwipe();
    });
    
    function handleSwipe() {
        const threshold = 100; // Мінімальна відстань для свайпу
        
        if (touchEndX - touchStartX > threshold) {
            // Свайп вправо (лайк)
            if (currentCard) {
                likeProfile(currentCard.dataset.profileId);
                showNextCard();
            }
        } else if (touchStartX - touchEndX > threshold) {
            // Свайп вліво (дизлайк)
            if (currentCard) {
                dislikeProfile(currentCard.dataset.profileId);
                showNextCard();
            }
        }
    }
}

// Лайк профілю (AJAX запит)
function likeProfile(profileId) {
    fetch(`/matches/like/${profileId}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.match) {
            // Якщо є метч, показати повідомлення
            showMatchAlert(data.matchedProfile);
        }
    })
    .catch(error => console.error('Error:', error));
}

// Дизлайк профілю (AJAX запит)
function dislikeProfile(profileId) {
    fetch(`/matches/dislike/${profileId}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json'
        }
    })
    .catch(error => console.error('Error:', error));
}

// Показати повідомлення про метч
function showMatchAlert(profile) {
    const matchAlert = document.createElement('div');
    matchAlert.className = 'match-alert';
    matchAlert.innerHTML = `
        <div class="match-alert-content">
            <h3>Вітаємо! У вас новий метч!</h3>
            <p>Ви отримали метч з ${profile.name}</p>
            <div class="match-alert-buttons">
                <button class="btn btn-primary" onclick="window.location.href='/chat/${profile.chatId}/'">Почати розмову</button>
                <button class="btn btn-secondary" onclick="closeMatchAlert()">Продовжити перегляд</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(matchAlert);
    
    // Додати клас для анімації з'явлення
    setTimeout(() => {
        matchAlert.classList.add('active');
    }, 10);
}

// Закрити повідомлення про метч
function closeMatchAlert() {
    const matchAlert = document.querySelector('.match-alert');
    if (matchAlert) {
        matchAlert.classList.remove('active');
        
        // Видалити елемент після анімації
        setTimeout(() => {
            matchAlert.remove();
        }, 300);
    }
}

// Показати повідомлення про відсутність профілів
function showNoMoreProfiles() {
    const container = document.querySelector('.swipe-container');
    if (container) {
        container.innerHTML = `
            <div class="no-profiles">
                <h3>Наразі немає більше профілів для перегляду</h3>
                <p>Спробуйте пізніше або змініть параметри пошуку</p>
                <button class="btn btn-primary" onclick="window.location.reload()">Оновити</button>
            </div>
        `;
    }
}

// Ініціалізація чату
function initChat() {
    const chatContainer = document.querySelector('.chat-container');
    if (!chatContainer) return;
    
    // Прокрутка чату донизу при завантаженні
    const messagesContainer = document.querySelector('.messages-container');
    if (messagesContainer) {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    
    // Відправка повідомлення
    const messageForm = document.querySelector('.message-form');
    if (messageForm) {
        messageForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const input = messageForm.querySelector('.message-input');
            const message = input.value.trim();
            
            if (message) {
                sendMessage(message, messageForm.dataset.chatId);
                input.value = '';
            }
        });
    }
    
    // Оновлення чату кожні 5 секунд
    setInterval(() => {
        if (messageForm && messageForm.dataset.chatId) {
            updateChat(messageForm.dataset.chatId);
        }
    }, 5000);
}

// Відправка повідомлення (AJAX запит)
function sendMessage(message, chatId) {
    fetch(`/chat/${chatId}/send/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            message: message
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            updateChat(chatId);
        }
    })
    .catch(error => console.error('Error:', error));
}

// Оновлення чату (AJAX запит)
function updateChat(chatId) {
    fetch(`/chat/${chatId}/messages/`, {
        method: 'GET'
    })
    .then(response => response.json())
    .then(data => {
        updateChatMessages(data.messages);
    })
    .catch(error => console.error('Error:', error));
}

// Оновлення повідомлень у чаті
function updateChatMessages(messages) {
    const messagesContainer = document.querySelector('.messages-container');
    if (!messagesContainer) return;
    
    // Попередня позиція прокрутки
    const wasAtBottom = messagesContainer.scrollHeight - messagesContainer.scrollTop === messagesContainer.clientHeight;
    
    // Очистити контейнер і додати нові повідомлення
    messagesContainer.innerHTML = '';
    
    messages.forEach(message => {
        const messageEl = document.createElement('div');
        messageEl.className = `message ${message.isMine ? 'message-outgoing' : 'message-incoming'}`;
        messageEl.innerHTML = `
            <div class="message-content">${message.content}</div>
            <div class="message-time">${message.timestamp}</div>
        `;
        
        messagesContainer.appendChild(messageEl);
    });
    
    // Прокрутити донизу, якщо користувач був внизу до оновлення
    if (wasAtBottom) {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
}

// Отримання значення CSRF токену з кукі
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}