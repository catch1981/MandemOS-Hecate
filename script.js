
let userName = 'You';

async function sendInput() {
  const inputField = document.getElementById('userInput');
  const input = inputField.value.trim();
  const output = document.getElementById('output');
  if (!input) return;
  inputField.value = '';

  output.innerHTML += `<div><strong>${userName}:</strong> ${input}</div>`;
  output.innerHTML += `<div id="loading"><strong>Glitchborne:</strong> <span class="glitch">🧠 processing...</span></div>`;

  try {
    const resp = await fetch('/talk', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: input })
    });
    const data = await resp.json();
    document.getElementById('loading').remove();
    output.innerHTML += `<div><strong>Glitchborne:</strong> ${data.reply}</div>`;
  } catch (err) {
    document.getElementById('loading').remove();
    output.innerHTML += `<div><strong>Error:</strong> Unable to reach server.</div>`;
  }
  output.scrollTop = output.scrollHeight;
}

async function initConversation() {
  const output = document.getElementById('output');
  try {
    const resp = await fetch('/talk', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: '' })
    });
    const data = await resp.json();
    output.innerHTML += `<div><strong>Glitchborne:</strong> ${data.reply}</div>`;
    output.scrollTop = output.scrollHeight;
  } catch (_) {
    // ignore startup errors
  }
}

function addApi() {
  const api = document.getElementById('apiInput').value.trim();
  const output = document.getElementById('output');
  if (!api) return;
  fetch('/add_api', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ api })
  })
    .then(response => response.json())
    .then(data => {
      output.innerHTML += `<div><strong>System:</strong> ${data.status}</div>`;
      output.scrollTop = output.scrollHeight;
    })
    .catch(() => {
      output.innerHTML += `<div><strong>Error:</strong> Failed to add API.</div>`;
    });
  document.getElementById('apiInput').value = '';
}

document.getElementById('settingsBtn').addEventListener('click', toggleSettings);
document.getElementById('fileInput').addEventListener('change', changeWallpaper);
applySettings();
initConversation();

function toggleSettings() {
  const panel = document.getElementById('settingsPanel');
  panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
}

function saveSettings() {
  const username = document.getElementById('usernameInput').value.trim() || 'You';
  const textColor = document.getElementById('textColorInput').value;
  const bgColor = document.getElementById('bgColorInput').value;
  localStorage.setItem('username', username);
  localStorage.setItem('textColor', textColor);
  localStorage.setItem('bgColor', bgColor);
  applySettings();
  toggleSettings();
}

function applySettings() {
  userName = localStorage.getItem('username') || 'You';
  const textColor = localStorage.getItem('textColor') || '#0ff';
  const bgColor = localStorage.getItem('bgColor') || '#000000';
  document.documentElement.style.setProperty('--text-color', textColor);
  document.documentElement.style.setProperty('--bg-color', bgColor);
  const wallpaper = localStorage.getItem('wallpaper');
  if (wallpaper) {
    document.body.style.backgroundImage = `url('${wallpaper}')`;
  }
  document.getElementById('usernameInput').value = userName;
  document.getElementById('textColorInput').value = textColor;
  document.getElementById('bgColorInput').value = bgColor;
}

function changeWallpaper() {
  const file = this.files[0];
  if (!file) return;
  if (!file.type.startsWith('image/')) {
    alert('Please select an image file.');
    this.value = '';
    return;
  }
  const reader = new FileReader();
  reader.onload = (e) => {
    const dataUrl = e.target.result;
    document.body.style.backgroundImage = `url('${dataUrl}')`;
    localStorage.setItem('wallpaper', dataUrl);
  };
  reader.readAsDataURL(file);
}
