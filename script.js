const chat = document.getElementById('chat');
const inputBox = document.getElementById('userInput');
const sendButton = document.getElementById('sendButton');

function appendMessage(text, className) {
  const div = document.createElement('div');
  div.className = `message ${className}`;
  div.textContent = text;
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
}

// Resolve the backend API base URL. When viewing the page directly from disk
// use the local server URL, otherwise default to the current origin so it
// works when hosted from the same domain.
const API_BASE = location.protocol === 'file:'
  ? 'http://localhost:8080'
  : location.origin;

async function sendInput() {
  const msg = inputBox.value.trim();
  if (!msg) return;
  appendMessage(msg, 'user');
  inputBox.value = '';
  inputBox.focus();
  try {
    const res = await fetch(`${API_BASE}/talk`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: msg })
    });
    const data = await res.json();
    appendMessage(data.reply, 'bot');
  } catch (e) {
    appendMessage('Error: could not reach server.', 'bot');
  }
}

function attachEvents() {
  sendButton.addEventListener('click', sendInput);
  inputBox.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      sendInput();
    }
  });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', attachEvents);
} else {
  attachEvents();
}
