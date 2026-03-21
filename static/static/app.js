// Connect to the backend via Socket.IO
const socket = io.connect("http://127.0.0.1:5000");  // Make sure this matches your backend URL

// Access DOM elements for user interaction
const sendButton = document.getElementById('send-button');
const userInput = document.getElementById('user-input');
const chatBox = document.getElementById('chat-box');
const userId = 1;  // Replace with dynamic user ID if needed

// Emit a message when the "Send" button is clicked
sendButton.addEventListener('click', () => {
    const userMessage = userInput.value.trim();
    if (userMessage) {
        socket.emit('send_message', { user_id: userId, message: userMessage });
        userInput.value = '';  // Clear the input field
    }
});

// Listen for incoming messages
socket.on('receive_message', function(data) {
    // Create a new message element
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', data.user_id === userId ? 'user' : 'ai');
    messageDiv.innerHTML = `<span>${data.user_id === userId ? 'You' : 'AI'}: </span>${data.message} <em>${data.timestamp}</em>`;
    
    // Append the message to the chat box
    chatBox.appendChild(messageDiv);
    chatBox.scrollTop = chatBox.scrollHeight;  // Scroll to the bottom of the chat box
});