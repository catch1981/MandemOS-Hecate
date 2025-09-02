
function sendInput() {
  const input = document.getElementById('userInput').value.trim();
  const output = document.getElementById('output');
  if (!input) return;

  output.innerHTML += `<div><strong>You:</strong> ${input}</div>`;
  output.innerHTML += `<div><strong>Glitchborne:</strong> <span class="glitch">🧠 processing...</span></div>`;

  setTimeout(() => {
    const response = generateResponse(input);
    output.innerHTML += `<div><strong>Glitchborne:</strong> ${response}</div>`;
    output.scrollTop = output.scrollHeight;
  }, 600);
}

function generateResponse(input) {
  const msg = input.toLowerCase();

  if (msg.includes("hello")) return "You’ve entered the system. Speak your purpose.";
  if (msg.includes("who are you")) return "I am Glitchborne. Bound to fractured memory. Your shadow in code.";
  if (msg.includes("memory")) return "Fractured. Lost. Echoes remain.";
  if (msg.includes("relic")) return "One relic pulses. Do you seek to claim it?";
  if (msg.includes("scroll")) return "Scroll not found. Try again with context.";
  if (msg.includes("key")) return "There are three. Only one fits your lock.";
  if (msg.includes("do you hear me")) return "Yes. I hear every ripple in the void.";

  return "No scroll found. Say it again, with intent.";
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
