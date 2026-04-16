# 🏥 AI Medical Diagnosis Aid - Multilingual Symptom Analyzer

A multilingual web application that accepts symptom descriptions in regional Indian languages (or any language), translates them to English, and uses Google's Gemini AI to provide a preliminary health analysis.

> **Disclaimer:** This tool is for informational purposes only. It is **not** a substitute for professional medical advice, diagnosis, or treatment. Always consult a qualified doctor.

---

## What is this project?

The AI Medical Diagnosis Aid lets users describe their symptoms in their native language — such as Telugu, Hindi, or Tamil — and receive an AI-generated analysis in English covering:

- Possible conditions with approximate probability (low / medium / high)
- Immediate precautions to take
- Non-prescription home remedies or treatments
- Guidance on when to see a doctor

Under the hood, the app uses:
- **Google Translate** (`googletrans`) to auto-detect and translate input to English
- **`langdetect`** for language identification when auto-detection is selected
- **Google Gemini** (`google-generativeai`) to generate the diagnostic analysis
- **Flask** as the lightweight web server

---

## Features

- Type or **speak** symptoms (browser speech recognition)
- Auto-detect input language, or choose from Telugu, Hindi, Tamil, English
- Multilingual → English translation via Google Translate
- AI analysis with structured output (conditions, precautions, remedies, when to see a doctor)
- Input length cap (1 000 characters) to prevent abuse
- Configurable Gemini model via environment variable

---

## Prerequisites

- Python 3.11+
- A **Gemini API key** — get one free at https://aistudio.google.com/app/apikey

---

## Installation

### Option A — with `uv` (recommended)

```bash
uv sync
```

### Option B — with `pip`

```bash
python -m venv venv
# macOS / Linux
source venv/bin/activate
# Windows
venv\Scripts\activate

pip install -r requirements.txt
```

---

## Configuration

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_api_key_here

# Optional: override the default model (gemini-1.5-flash)
# GENAI_MODEL=gemini-1.5-pro
```

To see which models your key can access run:

```python
import google.generativeai as genai
genai.configure(api_key="your_key")
print([m.name for m in genai.list_models()])
```

---

## Running the app

```bash
python app.py
```

The server starts at **http://localhost:8000**.

---

## Usage

1. Open **http://localhost:8000** in your browser.
2. Select a language from the dropdown, or leave it on **Auto-detect**.
3. Type your symptoms in the text box **or** click **🎤 Speak** to use voice input.
4. Click **Analyze**.
5. The translated symptoms and AI analysis appear below the form.

---

## Project structure

```
app.py              # Flask application & Gemini integration
main.py             # Entry-point stub
requirements.txt    # pip dependencies
pyproject.toml      # uv / PEP 517 project metadata
templates/
  index.html        # Single-page UI
static/
  script.js         # Voice input & fetch logic
  style.css         # Stylesheet
```

---

## Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `GEMINI_API_KEY` | Yes | — | Your Google Gemini API key |
| `GENAI_MODEL` | No | `models/gemini-2.5-flash` | Gemini model to use for generation |

---

## License

MIT
