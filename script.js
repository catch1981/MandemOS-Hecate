let lastReply = '';

async function sendToServer(text) {
  const res = await fetch('/talk', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: text })
  });
  const data = await res.json();
  return data.reply;
}

async function handleInput(text) {
  const output = document.getElementById('output');
  output.innerHTML += `<div><strong>You:</strong> ${text}</div>`;
  const status = document.createElement('div');
  status.id = 'lastReply';
  status.innerHTML = '<strong>Hecate:</strong> <span class="glitch">🧠 processing...</span>';
  output.appendChild(status);
  output.scrollTop = output.scrollHeight;
  try {
    const reply = await sendToServer(text);
    lastReply = reply;
    status.innerHTML = `<strong>Hecate:</strong> ${reply}`;
  } catch (e) {
    status.innerHTML = '<strong>Hecate:</strong> Error contacting server';
  }
  output.scrollTop = output.scrollHeight;
}

function initVoice() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) return null;
  const recog = new SpeechRecognition();
  recog.onresult = e => {
    const text = e.results[0][0].transcript;
    document.getElementById('userInput').value = '';
    handleInput(text);
  };
  return recog;
}

const recognizer = initVoice();

async function refreshFiles() {
  const res = await fetch('/files');
  const data = await res.json();
  const list = document.getElementById('fileList');
  list.innerHTML = '';
  data.files.forEach(f => {
    const opt = document.createElement('option');
    opt.value = f;
    opt.textContent = f;
    list.appendChild(opt);
  });
}

document.getElementById('submitButton').addEventListener('click', () => {
  const text = document.getElementById('userInput').value.trim();
  document.getElementById('userInput').value = '';
  if (text) handleInput(text);
});

document.getElementById('voiceButton').addEventListener('click', () => {
  if (recognizer) recognizer.start();
});

document.getElementById('speakButton').addEventListener('click', () => {
  if (!lastReply) return;
  const ut = new SpeechSynthesisUtterance(lastReply);
  speechSynthesis.speak(ut);
});

document.getElementById('refreshFiles').addEventListener('click', refreshFiles);

document.getElementById('downloadButton').addEventListener('click', () => {
  const file = document.getElementById('fileList').value;
  if (file) window.open(`/files/${encodeURIComponent(file)}`);
});

// initial load
refreshFiles();
