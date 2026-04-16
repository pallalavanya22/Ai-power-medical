document.addEventListener('DOMContentLoaded', function() {
    const symptomForm = document.getElementById('symptomForm');
    const symptoms = document.getElementById('symptoms');
    const sourceLang = document.getElementById('source_lang');
    const patientName = document.getElementById('patient_name');
    const patientAge = document.getElementById('patient_age');
    const patientPlace = document.getElementById('patient_place');
    const patientPhone = document.getElementById('patient_phone');
    const patientLang = document.getElementById('patient_lang');
    const documentInput = document.getElementById('document');
    const extractBtn = document.getElementById('extractBtn');
    const submitBtn = document.getElementById('submitBtn');
    const results = document.getElementById('results');
    const translatedDiv = document.getElementById('translated');
    const analysisDiv = document.getElementById('analysis');
    const backBtn = document.getElementById('backBtn');
    const speakBtn = document.getElementById('speak-btn');

    symptomForm.addEventListener('submit', function(e) {
        e.preventDefault();
        submitBtn.click();
    });

    // Voice
    let recognition;
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = true;
        recognition.lang = 'te-IN';
    }

    if (speakBtn) {
        speakBtn.addEventListener('click', function() {
            if (!recognition) {
                alert('Speech not supported');
                return;
            }
            recognition.lang = sourceLang.value === 'auto' ? 'te-IN' : sourceLang.value + '-IN';
            speakBtn.classList.add('active');
            speakBtn.textContent = '⏹️';
            recognition.start();
        });
        recognition.onresult = function(event) {
            let transcript = '';
            for (let i = event.resultIndex; i < event.results.length; i++) {
                transcript += event.results[i][0].transcript;
            }
            symptoms.value = transcript;
        };
        recognition.onend = function() {
            speakBtn.classList.remove('active');
            speakBtn.textContent = '🎤';
        };
    }

    // OCR extract
    if (extractBtn && documentInput) {
        extractBtn.addEventListener('click', function() {
            const files = documentInput.files;
            if (!files.length) return alert('Select file');

            extractBtn.disabled = true;
            extractBtn.textContent = 'Extracting...';

            const formData = new FormData();
            for (let file of files) formData.append('file', file);

            fetch('/extract', { method: 'POST', body: formData })
            .then(res => res.json())
            .then(data => {
                if (data.error) alert('Error: ' + data.error);
                else symptoms.value += (symptoms.value ? '\\n\\n' : '') + data.text;
            })
            .catch(err => alert('Extract failed'))
            .finally(() => {
                extractBtn.disabled = false;
                extractBtn.textContent = 'Extract text';
            });
        });
    }

    // Analyze - with debounce
    let analyzeTimeout;
    submitBtn.addEventListener('click', function() {
        if (analyzeTimeout) return;  // Debounce
        analyzeTimeout = setTimeout(() => {
            analyzeTimeout = null;
            const data = {
                symptoms: symptoms.value.trim(),
                source_lang: sourceLang.value,
                patient_name: patientName.value.trim(),
                patient_age: patientAge.value.trim(),
                patient_place: patientPlace.value.trim(),
                patient_phone: patientPhone.value.trim(),
                patient_lang: patientLang.value.trim(),
                history: []
            };

            if (!data.symptoms) return alert('Enter symptoms');

            submitBtn.disabled = true;
            submitBtn.textContent = 'Analyzing...';

            fetch('/diagnose', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            })
            .then(res => {
                if (!res.ok) throw new Error(`HTTP ${res.status}`);
                return res.json();
            })
            .then(result => {
                console.log('Result:', result);
                if (result.error) {
                    alert('Error: ' + result.error);
                } else {
                    document.getElementById('translated').innerHTML = `
                        <h3>📋 Translated (${result.detected_lang})</h3>
                        <pre>${result.translated || ''}</pre>`;
                    document.getElementById('analysis').innerHTML = marked.parse(result.analysis || '');
                    results.classList.remove('hidden');
                    results.scrollIntoView({behavior: 'smooth'});
                }
            })
            .catch(err => {
                console.error('Fetch error:', err);
                alert('Request failed - check console');
            })
            .finally(() => {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Analyze';
            });
        }, 500);
    });

    backBtn.addEventListener('click', function() {
        results.classList.add('hidden');
    });

    symptoms.addEventListener('keydown', e => {
        if (e.ctrlKey && e.key === 'Enter') submitBtn.click();
    });

    console.log('Script loaded');
});
