// JavaScript for dynamic input box resizing
document.getElementById('input-area').addEventListener('input', function() {
    this.style.height = 'auto';  // Reset height
    this.style.height = (this.scrollHeight) + 'px';  // Set new height
});

// Handle sending message
document.getElementById('send-btn').addEventListener('click', function() {
    const inputArea = document.getElementById('input-area');
    const message = inputArea.value.trim();

    if (message) {
        // Add user message to chat area
        const chatArea = document.getElementById('chat-area');
        const userMessage = document.createElement('div');
        userMessage.classList.add('chat-bubble', 'user-message');
        userMessage.textContent = message;
        chatArea.appendChild(userMessage);

        // Add bot response to chat area (placeholder)
        const botMessage = document.createElement('div');
        botMessage.classList.add('chat-bubble', 'bot-message');
        botMessage.textContent = "Bot response here...";  // Replace with real bot logic
        chatArea.appendChild(botMessage);

        // Auto-scroll to the latest message
        chatArea.scrollTop = chatArea.scrollHeight;

        // Clear input area
        inputArea.value = '';
    }
});

// Typing indicator logic
let typingTimeout;
const chatArea = document.getElementById('chat-area');

function showTypingIndicator() {
    const typingIndicator = document.createElement('div');
    typingIndicator.classList.add('chat-bubble', 'bot-message');
    typingIndicator.textContent = "Bot is typing...";
    chatArea.appendChild(typingIndicator);
    chatArea.scrollTop = chatArea.scrollHeight;

    // Remove typing indicator after 2 seconds
    clearTimeout(typingTimeout);
    typingTimeout = setTimeout(() => {
        chatArea.removeChild(typingIndicator);
    }, 2000);
}

// Trigger typing indicator when sending a message
document.getElementById('send-btn').addEventListener('click', function() {
    showTypingIndicator();
    // Simulate bot response
    setTimeout(() => {
        const botMessage = document.createElement('div');
        botMessage.classList.add('chat-bubble', 'bot-message');
        botMessage.textContent = "Here is the bot response.";
        chatArea.appendChild(botMessage);
        chatArea.scrollTop = chatArea.scrollHeight;
    }, 2000);  // Simulate delay for bot typing
});

// Keyboard navigation: send message with Enter key
document.getElementById('input-area').addEventListener('keydown', function(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        document.getElementById('send-btn').click();  // Trigger send button click
        event.preventDefault();  // Prevent new line when Enter is pressed
    }
});