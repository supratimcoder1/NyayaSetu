document.addEventListener('DOMContentLoaded', () => {
    const voiceBtn = document.getElementById('voice-btn');
    const userInput = document.getElementById('user-input');
    const listeningIndicator = document.getElementById('listening-indicator');

    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        const recognition = new SpeechRecognition();

        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'en-IN'; // Indian English

        recognition.onstart = () => {
            if (listeningIndicator) listeningIndicator.classList.remove('hidden');
        };

        recognition.onend = () => {
            if (listeningIndicator) listeningIndicator.classList.add('hidden');
        };

        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            userInput.value = transcript;
        };

        voiceBtn.addEventListener('click', () => {
            recognition.start();
        });
    } else {
        voiceBtn.style.display = 'none';
        console.log("Web Speech API not supported.");
    }
});
