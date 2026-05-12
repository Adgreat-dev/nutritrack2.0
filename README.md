# NutriTracker 🍏

NutriTracker is an AI-powered product analyzer that inspects images of product packaging or ingredient labels. Leveraging Google's Gemini API, it provides intelligent insights into the ingredients, fact-checks marketing claims, and computes an overall health score.

## Features ✨

- **Universal Analyzer:** Takes images of food, beverages, cosmetics, supplements, or household items and determines the category automatically.
- **Identify Product Names:** AI safely reads the physical label and intelligently returns the product name.
- **Ingredient Breakdown:** Extracts every ingredient from the label and categorizes it as good, bad, or neutral based on its purpose or scientific properties.
- **Fact-Check Claims:** Verifies any marketing claims (e.g., "100% All Natural", "Anti-aging") and cross-references them against the actual chemical composition to tell you whether the claim is verified or misleading.
- **Mock Fallback Mode:** To make development easier, if no valid API key is currently detected, NutriTracker falls back to rendering static mock data so you can continue building out the frontend.

## Tech Stack 🛠️

- **Backend:** Python + FastAPI
- **Frontend:** HTML5, Vanilla JavaScript, CSS3
- **AI Core:** Google `gemini-2.5-pro` model (`google-genai` client library)

## How to Run Locally 💻

Follow these simple steps from your terminal to run the NutriTracker locally on your machine.

### 1. Requirements
Ensure you have Python 3.8+ installed on your computer.

### 2. Setup the Virtual Environment
Navigate into the project directory and create/activate your isolated Python environment for this project.

**On Windows:**
```powershell
python -m venv venv
.\venv\Scripts\activate
```

**On macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
Install the required tools needed to run the app:
```bash
pip install fastapi uvicorn python-multipart google-genai
```

### 4. Setup AI Model (Ollama or Gemini)

NutriTracker can run entirely locally using Ollama (default), or it can use Google's Gemini API as a fallback.

**Option A: Local AI with Ollama (Recommended)**
1. Download and install [Ollama](https://ollama.com/).
2. Open your terminal and download the vision model (we use `llava` by default):
   ```bash
   ollama pull llava
   ```
3. Keep Ollama running in the background. The application is already configured to use it automatically!

**Option B: Cloud AI with Google Gemini (Alternative/Fallback)**
If you prefer to use Gemini or if Ollama fails, get an API key from [Google AI Studio](https://aistudio.google.com/), then set it in your environment:

**On Windows (PowerShell):**
```powershell
$env:GEMINI_API_KEY="your_api_key_here"
```

**On macOS / Linux:**
```bash
export GEMINI_API_KEY="your_api_key_here"
```

*(Note: If neither Ollama nor Gemini is set up, the backend will return mock data so you can still view the website layout).*

### 5. Start the Server
Run the local live-reloading server:
```bash
uvicorn main:app --reload
```

### 6. View the App ✨
Once you see `Application startup complete` in your terminal, open your favorite web browser and navigate to:
[http://localhost:8000](http://localhost:8000)

Enjoy tracking the truth behind the labels!
