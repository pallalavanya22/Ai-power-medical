import io
import logging
import os
from functools import wraps
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, session
from langdetect import detect
from PIL import Image
import pytesseract
from pdf2image import convert_from_bytes
from deep_translator import GoogleTranslator
import openai  # Use openai compat for Groq
from tenacity import retry, stop_after_attempt, wait_exponential
# LANGUAGES dict (common langs for India)
LANGUAGES = {
    'en': 'English',
    'hi': 'Hindi',
    'te': 'Telugu',
    'ta': 'Tamil',
    'bn': 'Bengali',
    'mr': 'Marathi',
    'gu': 'Gujarati',
    'kn': 'Kannada',
    'ml': 'Malayalam',
    'pa': 'Punjabi',
    'ur': 'Urdu',
    'auto': 'Auto-detect'
}

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-change-in-prod')

GROQ_API_KEY = os.getenv('GROQ_API_KEY')
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not set in .env. Add it!")

# OpenAI-compatible client for Groq
client = openai.OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
)

MODELS = ["llama-3.3-70b-versatile", "llama3-groq-70b-8192-tool-use-preview"]
logger.info("Groq models ready: %s", MODELS)

translator = GoogleTranslator(source='auto', target='en')

MAX_SYMPTOMS_LENGTH = 50000

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/extract', methods=['POST'])
def extract_text():
    files = request.files.getlist('file')
    if not files:
        return jsonify({'error': 'No file uploaded'}), 400

    try:
        text = ''
        for file in files:
            if not file or file.filename == '':
                continue

            file_bytes = file.read()

            if file.content_type == 'application/pdf' or file.filename.lower().endswith('.pdf'):
                images = convert_from_bytes(file_bytes)
                for idx, page in enumerate(images, start=1):
                    page_text = pytesseract.image_to_string(page, lang='eng+hin')
                    text += f"\n\n--- {file.filename} - Page {idx} ---\n\n" + page_text
            else:
                image = Image.open(io.BytesIO(file_bytes))
                text += f"\n\n--- {file.filename} ---\n\n" + pytesseract.image_to_string(image, lang='eng+hin')

        lang_code = detect(text) if text else 'en'
        lang_name = LANGUAGES.get(lang_code, 'English')

        return jsonify({
            'text': text,
            'lang_code': lang_code,
            'detected_lang': lang_name
        })
    except Exception as e:
        logger.exception("OCR failed")
        return jsonify({'error': str(e)}), 500

@app.route('/diagnose', methods=['POST'])
def diagnose():
    data = request.json
    symptoms = data.get('symptoms', '').strip()
    source_lang = data.get('source_lang', 'auto')
    history = data.get('history', [])

    patient_name = data.get('patient_name', '').strip()
    patient_age = data.get('patient_age', '').strip()
    patient_place = data.get('patient_place', '').strip()
    patient_phone = data.get('patient_phone', '').strip()
    patient_lang = data.get('patient_lang', '').strip()

    if not symptoms:
        return jsonify({'error': 'Symptoms required'}), 400
    if len(symptoms) > MAX_SYMPTOMS_LENGTH:
        return jsonify({'error': f'Too long (max {MAX_SYMPTOMS_LENGTH} chars)'}), 400

    if 'chat_history' not in session:
        session['chat_history'] = []
        session['patient_info'] = {}
    session_history = session['chat_history']

    try:
        source_lang = detect(symptoms) if source_lang == 'auto' else source_lang
        lang_name = LANGUAGES.get(source_lang, 'English')

        eng_symptoms = translator.translate(symptoms)
        translated = f"Translated ({lang_name}): {eng_symptoms}"

        # Patient info
        if any([patient_name, patient_age, patient_place, patient_phone, patient_lang]):
            session['patient_info'].update({
                'name': patient_name, 'age': patient_age, 'place': patient_place,
                'phone': patient_phone, 'lang': patient_lang
            })
        pinfo = session.get('patient_info', {})
        patient_info = '\n'.join([f"{k.capitalize()}: {v}" for k, v in pinfo.items() if v]) + '\n'
        greeting_name = pinfo.get('name', 'friend')

        history_text = '\n'.join([f"{ 'Patient' if m['role'] == 'user' else 'Doctor' }: {m['content']}" for m in history])

        full_prompt = f"""Namaste! Give DETAILED advice for Indian patient with limited education. Use SIMPLE words, bullet points, lots of lines.

Symptoms: {eng_symptoms}
Patient: {patient_info}
Language: {lang_name}

**MANDATORY STRUCTURE (more sections, 50+ lines total)**:

1. **Namaste {greeting_name}!** Don't worry, here's detailed help...

2. **🏥 What might be wrong (3 possible causes, explain simply):**
   - 
   - 
   - 

3. **💊 HOME REMEDIES (10+ easy village remedies):**
   - Ginger tea recipe + how
   - Jeera water how to make
   - Buttermilk benefits
   - Haldi milk
   - Tulsi tea
   - Garlic clove chew
   - Coconut water
   - etc (list 10+)

4. **✅ WHY these work (explain each remedy):**
   - Ginger: 
   - Jeera: 
   - etc (detail)

5. **🍲 DAILY DIET CHART for 3 days:**
   - Breakfast: 
   - Lunch: 
   - Dinner:
   - Snacks:

6. **⚠️ NEVER DO these + when DANGER (EMERGENCY signs):**
   - Stop if:
   - Rush to hospital if blood, chest pain, fainting etc

7. **🏠 DAILY ROUTINE:**
   - Wake up:
   - Morning walk:
   - Meals:
   - Bedtime:

8. **💰 CHEAP MEDICINES from village shop (with dose):**
   - Eno for gas
   - Crocin for fever
   - etc

9. **📞 DOCTOR NUMBERS + when to call:**
   - 108 ambulance
   - Local PHC:
   - When:

10. **✅ TRACK PROGRESS (checklist):**
    - Day 1: 
    - Day 2: 

Use emojis everywhere. **MANY LINES, DETAILED for uneducated patients**. Respond ONLY in {lang_name}.

Example stomach pain (expand like this):"""
        # Truncated - but now MUCH longer prompt for more lines/output

        def generate_with_retry(model_idx=0):
            for attempt in range(3):
                try:
                    model = MODELS[model_idx]
                    logger.info(f"Generating with {model} (attempt {attempt+1})")
                    response = client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": full_prompt}],
                        temperature=0.7,
                        max_tokens=4000  # Increased for long output
                    )
                    return response.choices[0].message.content
                except Exception as e:
                    logger.warning(f"Attempt {attempt+1} failed: {e}")
                    if 'rate' in str(e).lower():
                        import time
                        time.sleep(2 ** attempt)
                    model_idx = (model_idx + 1) % len(MODELS)
            raise Exception("Retries exhausted")

        analysis_en = generate_with_retry()
        analysis = analysis_en

        # Back translate
        if source_lang != 'en':
            try:
                analysis = GoogleTranslator(source='en', target=source_lang).translate(analysis_en)
            except:
                pass

        session_history.append({'role': 'user', 'content': eng_symptoms, 'lang': lang_name})
        session_history.append({'role': 'assistant', 'content': analysis_en})
        session['chat_history'] = session_history[-20:]

        return jsonify({
            'translated': translated,
            'analysis': analysis,
            'analysis_en': analysis_en,
            'history': session_history,
            'detected_lang': lang_name
        })

    except Exception as e:
        logger.error(f"Diagnosis error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host="localhost", port=8000)

