const classifyBtn = document.getElementById('classifyBtn');
const issueText = document.getElementById('issueText');
const serviceSelect = document.getElementById('serviceSelect');
const voiceBtn = document.getElementById('voiceBtn');

function showToast(message, type = 'success') {
  const stack = document.getElementById('toastStack');
  if (!stack) return;
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.textContent = message;
  stack.appendChild(el);
  setTimeout(() => el.remove(), 2600);
}

if (classifyBtn) {
  classifyBtn.addEventListener('click', async () => {
    const message = issueText.value.trim();
    if (!message) {
      showToast('Please describe your issue first.', 'error');
      return;
    }

    const response = await fetch('/api/classify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message })
    });

    if (!response.ok) {
      showToast('Unable to analyze issue right now.', 'error');
      return;
    }

    const data = await response.json();
    for (let i = 0; i < serviceSelect.options.length; i += 1) {
      if (serviceSelect.options[i].value === data.service) {
        serviceSelect.selectedIndex = i;
        showToast(`Detected service: ${data.service}`);
        break;
      }
    }
  });
}

if (voiceBtn) {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    voiceBtn.disabled = true;
    voiceBtn.textContent = 'Voice unavailable';
  } else {
    const recognition = new SpeechRecognition();
    recognition.lang = 'en-US';
    recognition.onresult = (event) => {
      issueText.value = event.results[0][0].transcript;
      showToast('Voice captured.');
    };
    voiceBtn.addEventListener('click', () => recognition.start());
  }
}
