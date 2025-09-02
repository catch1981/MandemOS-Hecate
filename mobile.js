const output = document.getElementById('output');
const input = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');
const speakBtn = document.getElementById('speakBtn');
const locBtn = document.getElementById('locBtn');
const fileBtn = document.getElementById('fileBtn');
const fileInput = document.getElementById('fileInput');
const imgBtn = document.getElementById('imgBtn');
const imgInput = document.getElementById('imgInput');

async function sendMessage(message) {
  output.innerHTML += `<div><strong>You:</strong> ${message}</div>`;
  try {
    const res = await fetch('/talk', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message })
    });
    const data = await res.json();
    output.innerHTML += `<div><strong>Hecate:</strong> ${data.reply}</div>`;
  } catch (err) {
    output.innerHTML += `<div><strong>Error:</strong> ${err.message}</div>`;
  }
  output.scrollTop = output.scrollHeight;
}

sendBtn.addEventListener('click', () => {
  const msg = input.value.trim();
  if (!msg) return;
  input.value = '';
  sendMessage(msg);
});

async function uploadFile(file) {
  output.innerHTML += `<div><strong>You (file):</strong> ${file.name}</div>`;
  const fd = new FormData();
  fd.append('file', file);
  try {
    const res = await fetch('/talk/file', { method: 'POST', body: fd });
    const data = await res.json();
    output.innerHTML += `<div><strong>Hecate:</strong> ${data.reply}</div>`;
    if (data.data && data.mimetype) {
      if (data.mimetype.startsWith('image/')) {
        output.innerHTML += `<div><img src="data:${data.mimetype};base64,${data.data}" alt="${data.filename}" /></div>`;
      } else {
        output.innerHTML += `<div><a href="data:${data.mimetype};base64,${data.data}" download="${data.filename}">Download ${data.filename}</a></div>`;
      }
    }
  } catch (err) {
    output.innerHTML += `<div><strong>Error:</strong> ${err.message}</div>`;
  }
  output.scrollTop = output.scrollHeight;
}

fileBtn.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', () => {
  const file = fileInput.files[0];
  if (file) {
    uploadFile(file);
    fileInput.value = '';
  }
});

imgBtn.addEventListener('click', () => imgInput.click());
imgInput.addEventListener('change', () => {
  const file = imgInput.files[0];
  if (file) {
    uploadFile(file);
    imgInput.value = '';
  }
});

let mediaRecorder;
let chunks = [];

speakBtn.addEventListener('click', async () => {
  if (mediaRecorder && mediaRecorder.state === 'recording') {
    mediaRecorder.stop();
    speakBtn.textContent = 'Speak';
    return;
  }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    chunks = [];
    mediaRecorder.ondataavailable = e => chunks.push(e.data);
    mediaRecorder.onstop = async () => {
      const blob = new Blob(chunks, { type: 'audio/webm' });
      const fd = new FormData();
      fd.append('file', blob, 'input.webm');
      try {
        const res = await fetch('/talk/audio', { method: 'POST', body: fd });
        const data = await res.json();
        output.innerHTML += `<div><strong>You (voice):</strong> ${data.transcript || ''}</div>`;
        output.innerHTML += `<div><strong>Hecate:</strong> ${data.reply}</div>`;
      } catch (err) {
        output.innerHTML += `<div><strong>Error:</strong> ${err.message}</div>`;
      }
      output.scrollTop = output.scrollHeight;
    };
    mediaRecorder.start();
    speakBtn.textContent = 'Stop';
  } catch (err) {
    output.innerHTML += `<div><strong>Error:</strong> ${err.message}</div>`;
  }
});

locBtn.addEventListener('click', () => {
  if (!navigator.geolocation) {
    output.innerHTML += '<div><strong>Error:</strong> Geolocation not supported.</div>';
    return;
  }
  navigator.geolocation.getCurrentPosition(pos => {
    const { latitude, longitude } = pos.coords;
    const msg = `location:${latitude}|${longitude}`;
    sendMessage(msg);
  }, err => {
    output.innerHTML += `<div><strong>Error:</strong> ${err.message}</div>`;
  });
});
