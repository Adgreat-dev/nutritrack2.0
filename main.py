from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import os
import json
import time
import traceback
import logging
import base64
import requests
import io
try:
    from PIL import Image
except ImportError:
    Image = None
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ── SDK import ────────────────────────────────────────────────────────────────
try:
    from google import genai
    from google.genai import types
    import importlib.metadata
    SDK_VERSION = importlib.metadata.version("google-genai")
    logger.info(f"google-genai SDK version: {SDK_VERSION}")
    GENAI_OK = True
except ImportError:
    genai = types = None
    SDK_VERSION = None
    GENAI_OK = False
    logger.error("google-genai not installed. Run: pip install google-genai")

app = FastAPI(title="VerifAI API")
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# ── API key ───────────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyBfX30-OAM6dddgWXqy6LR2GmHAfUe1Fv8")

client = None
if GENAI_OK and GEMINI_API_KEY:
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        logger.info("Gemini client ready.")
    except Exception as e:
        logger.error(f"Client init failed: {e}")

# ── Model config ──────────────────────────────────────────────────────────────
# gemini-2.0-flash is the model available on the free tier.
# It supports vision (image input) and is fast.
PRIMARY_MODEL   = "gemini-2.5-flash"
RATE_LIMIT_WAIT = 30   # seconds to wait before retrying on a 429
MAX_RETRIES     = 2    # number of rate-limit retries

# ── Ollama config ─────────────────────────────────────────────────────────────
USE_OLLAMA = os.getenv("USE_OLLAMA", "true").lower() == "true"
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llava")

# ── Prompt ────────────────────────────────────────────────────────────────────
PROMPT = """Analyze this product packaging image carefully.
First, determine the exact product category. Is it a Food, Beverage, Cosmetic, Supplement, or Household item?

Return ONLY a valid JSON object matching exactly this structure:

{
    "productName": "extract the exact name of the product from the label",
    "category": "Food | Beverage | Cosmetic | Supplement | Skincare | Household",
    "score": 50,
    "ingredients": [
        {
            "name": "ingredient name exactly as on the label",
            "status": "good",
            "reason": "1 sentence: what it does and why it is good, bad, or neutral."
        }
    ],
    "claims": [
        {
            "claim": "marketing claim exactly as written on label",
            "isReal": true,
            "explanation": "1 sentence on whether accurate or misleading."
        }
    ]
}

CRITICAL OCR RULES:
1. DO NOT guess or hallucinate product names (e.g. do not invent "Easy Shampoo"). Read the actual largest text on the bottle.
2. Look for the "INGREDIENTS:" list. You MUST extract each ingredient individually. DO NOT summarize them into a single sentence.
3. If you cannot read the ingredients because it is too blurry, return an empty array [] for ingredients.
4. status MUST be exactly one of: "good", "neutral", "bad".
5. Return ONLY raw JSON starting with {. No markdown fences.
"""

def _strip_fences(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw[3:]
        if raw.startswith("json"):
            raw = raw[4:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()
    return raw

def call_gemini(image_bytes: bytes, mime: str) -> dict:
    """
    Call gemini-2.0-flash with automatic retry on rate-limit (429).
    """
    text_part  = types.Part.from_text(text=PROMPT)
    image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime)
    contents   = [types.Content(role="user", parts=[text_part, image_part])]
    config     = types.GenerateContentConfig(
        response_mime_type="application/json",
        temperature=0.2,
    )

    for attempt in range(1, MAX_RETRIES + 2):
        try:
            logger.info(f"Calling {PRIMARY_MODEL} (attempt {attempt})")
            response = client.models.generate_content(
                model=PRIMARY_MODEL,
                contents=contents,
                config=config,
            )

            if response.text is None:
                finish = None
                try:
                    finish = response.candidates[0].finish_reason
                except Exception:
                    pass
                raise ValueError(
                    f"Model returned an empty response (finish_reason={finish}). "
                    "The image may have been blocked by a safety filter."
                )

            raw    = _strip_fences(response.text)
            result = json.loads(raw)

            result.setdefault("productName", "Unknown Product")
            result.setdefault("category", "Product")
            result.setdefault("ingredients", [])
            result.setdefault("claims", [])
            
            # Deterministic Score Calculation
            score = 100
            for ing in result.get("ingredients", []):
                status = ing.get("status", "neutral").lower()
                if status == "bad":
                    score -= 30
                elif status == "neutral":
                    score -= 5
            
            result["score"] = max(0, min(100, score))

            logger.info(f"Success — {result['productName']} (computed score {result['score']})")
            return result

        except json.JSONDecodeError as e:
            preview = response.text[:300] if response and response.text else "N/A"
            logger.error(f"JSON decode error: {e} | Raw: {preview!r}")
            raise ValueError(f"AI returned malformed JSON: {e}") from e

        except ValueError:
            raise

        except Exception as e:
            err_str = str(e).lower()
            is_rate_limit = any(kw in err_str for kw in [
                "429", "rate", "quota", "resource_exhausted",
                "too many requests", "exhausted"
            ])
            if is_rate_limit:
                if attempt <= MAX_RETRIES:
                    logger.warning(
                        f"Rate limited. Waiting {RATE_LIMIT_WAIT}s before retry "
                        f"({attempt}/{MAX_RETRIES})..."
                    )
                    import time
                    time.sleep(RATE_LIMIT_WAIT)
                    continue
                else:
                    break
            logger.error(f"Gemini call failed:\n{traceback.format_exc()}")
            raise

    raise RuntimeError(
        f"Still rate-limited after {MAX_RETRIES} retries. "
    )

def call_ollama(image_bytes: bytes, mime: str) -> dict:
    """
    Call local Ollama model with the image.
    """
    logger.info(f"Calling local Ollama model: {OLLAMA_MODEL}")
    
    # Force conversion to JPEG and downsize to prevent Ollama from crashing (500 Server Error)
    if Image is not None:
        try:
            img = Image.open(io.BytesIO(image_bytes))
            if img.mode != 'RGB':
                img = img.convert('RGB')
            # Increased thumbnail size to 1600 so OCR can read tiny ingredients text
            img.thumbnail((1600, 1600))
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=85)
            image_bytes = buffer.getvalue()
        except Exception as e:
            logger.error(f"Failed to decode or resize image with PIL: {e}")
            raise ValueError(f"Could not decode image format. Please upload a standard JPG or PNG. Error: {e}")
    else:
        logger.warning("Pillow is not installed. Sending raw bytes to Ollama.")
            
    # Base64 encode the image
    b64_image = base64.b64encode(image_bytes).decode('utf-8')
    
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": PROMPT,
        "images": [b64_image],
        "stream": False
    }
    
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        response.raise_for_status()
        
        data = response.json()
        raw = data.get("response", "")
        raw = _strip_fences(raw)
        
        result = json.loads(raw)
        
        # Apply defaults in case the model missed some fields
        result.setdefault("productName", "Unknown Product")
        result.setdefault("category", "Product")
        result.setdefault("ingredients", [])
        result.setdefault("claims", [])
        
        # Deterministic Score Calculation
        score = 100
        for ing in result.get("ingredients", []):
            status = ing.get("status", "neutral").lower()
            if status == "bad":
                score -= 30
            elif status == "neutral":
                score -= 5
        
        result["score"] = max(0, min(100, score))
        
        logger.info(f"Ollama Success — {result['productName']} (computed score {result['score']})")
        return result
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Ollama connection error: {e}")
        raise ValueError(f"Raw Ollama Error: {repr(e)}") from e
    except json.JSONDecodeError as e:
        preview = raw[:300] if 'raw' in locals() and raw else "N/A"
        logger.error(f"Ollama JSON decode error: {e} | Raw: {preview!r}")
        raise ValueError(f"Ollama returned malformed JSON: {e}") from e



# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def read_index():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()


@app.get("/api/health")
async def health():
    """Visit http://localhost:8000/api/health to check your setup."""
    info = {
        "use_ollama":    USE_OLLAMA,
        "ollama_model":  OLLAMA_MODEL,
        "sdk_installed": GENAI_OK,
        "sdk_version":   SDK_VERSION,
        "api_key_set":   bool(GEMINI_API_KEY),
        "client_ready":  client is not None,
        "gemini_model":  PRIMARY_MODEL,
    }
    if client:
        try:
            r = client.models.generate_content(
                model=PRIMARY_MODEL,
                contents="Reply with valid JSON only: {\"ok\": true}",
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.0,
                    max_output_tokens=10,
                ),
            )
            info["model_reachable"] = bool(r.text)
            info["model_response"]  = r.text
        except Exception as e:
            info["model_reachable"] = False
            info["model_error"]     = str(e)
    return JSONResponse(content=info)


@app.post("/api/analyze")
async def analyze_image(image: UploadFile = File(...)):
    try:
        content = await image.read()
        mime    = image.content_type or "image/jpeg"

        logger.info(f"Upload: {image.filename!r} | {mime} | {len(content)} bytes")

        if not content:
            return JSONResponse({"error": "Uploaded file is empty."}, status_code=400)
        if not mime.startswith("image/"):
            return JSONResponse({"error": f"Expected an image, got: {mime}"}, status_code=400)

        ollama_error = "Unknown"
        if USE_OLLAMA:
            try:
                result = call_ollama(content, mime)
                return JSONResponse(content=result)
            except Exception as e:
                ollama_error = str(e)
                logger.warning(f"Ollama API call failed: {e}. Falling back to Gemini (if available).")
        
        if client:
            try:
                result = call_gemini(content, mime)
                return JSONResponse(content=result)
            except Exception as e:
                logger.warning(f"Gemini API call failed: {e}. Falling back to mock data.")

        # Mock fallback (no client or call failed)
        logger.warning("No Gemini client or API failed — mock data returned.")
        return JSONResponse(content={
            "productName": f"⚠️ Mock — Ollama Error: {ollama_error[:100]}",
            "category": "Error",
            "score": 45,
            "ingredients": [
                {"name": "Error details", "status": "bad", "reason": f"Ollama failed with: {ollama_error}"},
            ],
            "claims": [],
        })

    except RuntimeError as e:
        # Rate limit exhausted after retries
        logger.error(str(e))
        return JSONResponse({"error": str(e)}, status_code=429)

    except ValueError as e:
        logger.error(f"ValueError: {e}")
        return JSONResponse({"error": str(e)}, status_code=502)

    except Exception as e:
        logger.error(f"Unhandled error:\n{traceback.format_exc()}")
        return JSONResponse({"error": str(e)}, status_code=500)