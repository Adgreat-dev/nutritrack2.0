from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import os
import json
import time
import traceback
import logging

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

# ── Prompt ────────────────────────────────────────────────────────────────────
PROMPT = """Analyze this product packaging image carefully.
Identify the product type (food, beverage, cosmetic, supplement, cleaning product, etc.).

Return ONLY a valid JSON object — no markdown, no code fences, no explanation.

{
    "productName": "name from the label",
    "category": "Food | Beverage | Cosmetic | Supplement | Skincare | Household",
    "score": <integer 0-100>,
    "ingredients": [
        {
            "name": "ingredient name exactly as on the label",
            "status": "good",
            "reason": "2-3 sentences: what it does, health impacts, why this status."
        }
    ],
    "claims": [
        {
            "claim": "marketing claim exactly as written on label",
            "isReal": true,
            "explanation": "2-3 sentences on whether accurate or misleading."
        }
    ]
}

status must be exactly one of: "good"  "neutral"  "bad"
isReal must be a boolean: true or false (not a string)

Scoring: 70-100 = healthy/safe | 40-69 = moderate | 0-39 = concerning
Extract EVERY ingredient and EVERY marketing claim visible on the label.
If no claims are visible, return: "claims": []
Analyze only what is actually in the image — do not invent or assume data."""


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

    for attempt in range(1, MAX_RETRIES + 2):  # attempts: 1, 2, 3
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
            result.setdefault("score", 50)
            result.setdefault("ingredients", [])
            result.setdefault("claims", [])
            result["score"] = max(0, min(100, int(result["score"])))

            logger.info(f"Success — {result['productName']} (score {result['score']})")
            return result

        except json.JSONDecodeError as e:
            preview = response.text[:300] if response and response.text else "N/A"
            logger.error(f"JSON decode error: {e} | Raw: {preview!r}")
            raise ValueError(f"AI returned malformed JSON: {e}") from e

        except ValueError:
            raise  # our own errors — don't retry

        except Exception as e:
            err_str = str(e).lower()

            # Rate limit (429) — wait and retry
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
                    time.sleep(RATE_LIMIT_WAIT)
                    continue
                else:
                    break

            # Any other error — log full traceback and raise
            logger.error(f"Gemini call failed:\n{traceback.format_exc()}")
            raise

    raise RuntimeError(
        f"Still rate-limited after {MAX_RETRIES} retries. "
        "Free tier allows ~2 requests/min. Please wait a moment and try again."
    )


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def read_index():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()


@app.get("/api/health")
async def health():
    """Visit http://localhost:8000/api/health to check your setup."""
    info = {
        "sdk_installed": GENAI_OK,
        "sdk_version":   SDK_VERSION,
        "api_key_set":   bool(GEMINI_API_KEY),
        "client_ready":  client is not None,
        "model":         PRIMARY_MODEL,
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

        if client:
            try:
                result = call_gemini(content, mime)
                return JSONResponse(content=result)
            except Exception as e:
                logger.warning(f"Gemini API call failed: {e}. Falling back to mock data.")

        # Mock fallback (no client or call failed)
        logger.warning("No Gemini client or API failed — mock data returned.")
        return JSONResponse(content={
            "productName": "⚠️ Mock — Gemini API failed or not connected",
            "category": "Food",
            "score": 45,
            "ingredients": [
                {"name": "Water / Aqua",         "status": "neutral", "reason": "Primary base solvent. Safe and inert."},
                {"name": "Artificial Fragrance",  "status": "bad",     "reason": "Undisclosed synthetic chemicals. Common allergen."},
                {"name": "Sodium Lauryl Sulfate", "status": "bad",     "reason": "Harsh surfactant. Disrupts skin barrier with repeated use."},
                {"name": "Aloe Vera Extract",     "status": "good",    "reason": "Anti-inflammatory and hydrating. Promotes skin recovery."},
            ],
            "claims": [
                {"claim": "100% All Natural", "isReal": False, "explanation": "Misleading — contains synthetic Fragrance and SLS."},
                {"claim": "Made with Real Ingredients", "isReal": True, "explanation": "Technically true, but used as a marketing halo."},
            ],
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