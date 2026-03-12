const classifyBtn = document.getElementById('classifyBtn');
const issueText = document.getElementById('issueText');
const serviceSelect = document.getElementById('serviceSelect');
const voiceBtn = document.getElementById('voiceBtn');

if (classifyBtn) {
  classifyBtn.addEventListener('click', async () => {
    const message = issueText.value.trim();
    if (!message) {
      alert('Please describe your issue first.');
      return;
    }

    const response = await fetch('/api/classify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message })
    });

    if (!response.ok) {
      alert('Unable to analyze issue right now.');
      return;
    }

    const data = await response.json();
    for (let i = 0; i < serviceSelect.options.length; i += 1) {
      if (serviceSelect.options[i].value === data.service) {
        serviceSelect.selectedIndex = i;
        break;
      }
    }
  });
}

if (voiceBtn) {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    voiceBtn.disabled = true;
    voiceBtn.textContent = 'Voice Input Unavailable';
  } else {
    const recognition = new SpeechRecognition();
    recognition.lang = 'en-US';
    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      issueText.value = transcript;
    };
    voiceBtn.addEventListener('click', () => recognition.start());
  }
}
