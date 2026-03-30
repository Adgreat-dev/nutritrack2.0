"""
VerifAI — Gemini Debug Script
Run this directly on your machine to see the exact error:
    python debug_gemini.py
It will tell you exactly what's broken and how to fix it.
"""

import sys
import json
import os

API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyBfX30-OAM6dddgWXqy6LR2GmHAfUe1Fv8")
TEST_IMAGE_PATH = None  # set to a local image path to test with real image, e.g. "label.jpg"

print("=" * 60)
print("VerifAI — Gemini Diagnostic")
print("=" * 60)

# ── Step 1: Check package ─────────────────────────────────────────────────────
print("\n[1] Checking google-genai package...")
try:
    from google import genai
    from google.genai import types
    import importlib.metadata
    try:
        ver = importlib.metadata.version("google-genai")
        print(f"    ✓ Installed: google-genai=={ver}")
    except Exception:
        print("    ✓ Installed (version unknown)")
except ImportError as e:
    print(f"    ✗ NOT installed: {e}")
    print("    Fix: pip install google-genai")
    sys.exit(1)

# ── Step 2: Check API key ─────────────────────────────────────────────────────
print("\n[2] Checking API key...")
if not API_KEY:
    print("    ✗ API key is empty")
    sys.exit(1)
print(f"    Key prefix: {API_KEY[:8]}...")

# ── Step 3: Initialize client ─────────────────────────────────────────────────
print("\n[3] Initializing client...")
try:
    client = genai.Client(api_key=API_KEY)
    print("    ✓ Client created")
except Exception as e:
    print(f"    ✗ Client init failed: {e}")
    sys.exit(1)

# ── Step 4: List available models ─────────────────────────────────────────────
print("\n[4] Listing available models (those that support generateContent)...")
try:
    available = []
    for m in client.models.list():
        name = getattr(m, 'name', '') or ''
        supported = getattr(m, 'supported_actions', []) or []
        if 'generateContent' in str(supported) or 'generate_content' in str(supported):
            available.append(name)
            print(f"    ✓ {name}")
    if not available:
        # fallback: just print all models
        print("    (couldn't filter by action, listing all)")
        for m in client.models.list():
            print(f"    - {getattr(m, 'name', m)}")
except Exception as e:
    print(f"    ✗ Could not list models: {e}")

# ── Step 5: Try each model with a simple text-only call ──────────────────────
MODELS_TO_TRY = [
    "gemini-2.5-pro",
    "gemini-2.0-flash",
    "gemini-1.5-pro",
    "gemini-1.5-flash",
    "gemini-pro",
]

print("\n[5] Testing generate_content with each model (text only)...")
working_model = None
for model_name in MODELS_TO_TRY:
    try:
        resp = client.models.generate_content(
            model=model_name,
            contents="Reply with exactly this JSON and nothing else: {\"ok\": true}",
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.0,
                max_output_tokens=20,
            ),
        )
        text = resp.text
        print(f"    ✓ {model_name} → {repr(text)}")
        if working_model is None:
            working_model = model_name
    except Exception as e:
        print(f"    ✗ {model_name} → {e}")

if working_model is None:
    print("\n    ✗ No models worked. Check your API key and billing at https://aistudio.google.com")
    sys.exit(1)

print(f"\n    Best model to use: {working_model}")

# ── Step 6: Test with image bytes (tiny 1x1 PNG) ─────────────────────────────
print(f"\n[6] Testing image upload with {working_model}...")
try:
    # Minimal valid 1×1 white PNG (67 bytes)
    TINY_PNG = bytes([
        0x89,0x50,0x4E,0x47,0x0D,0x0A,0x1A,0x0A,0x00,0x00,0x00,0x0D,0x49,0x48,0x44,0x52,
        0x00,0x00,0x00,0x01,0x00,0x00,0x00,0x01,0x08,0x02,0x00,0x00,0x00,0x90,0x77,0x53,
        0xDE,0x00,0x00,0x00,0x0C,0x49,0x44,0x41,0x54,0x08,0xD7,0x63,0xF8,0xFF,0xFF,0x3F,
        0x00,0x05,0xFE,0x02,0xFE,0xDC,0xCC,0x59,0xE7,0x00,0x00,0x00,0x00,0x49,0x45,0x4E,
        0x44,0xAE,0x42,0x60,0x82
    ])

    if TEST_IMAGE_PATH and os.path.exists(TEST_IMAGE_PATH):
        with open(TEST_IMAGE_PATH, "rb") as f:
            image_bytes = f.read()
        mime = "image/jpeg"
        print(f"    Using real image: {TEST_IMAGE_PATH}")
    else:
        image_bytes = TINY_PNG
        mime = "image/png"
        print("    Using built-in 1×1 test image (set TEST_IMAGE_PATH for real test)")

    # Try the exact call structure from main.py
    text_part  = types.Part.from_text(text="What color is this image? Reply with JSON: {\"color\": \"...\"}")
    image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime)

    resp = client.models.generate_content(
        model=working_model,
        contents=[types.Content(role="user", parts=[text_part, image_part])],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.0,
        ),
    )
    print(f"    ✓ Image call succeeded → {repr(resp.text)}")

except Exception as e:
    print(f"    ✗ Image call failed: {type(e).__name__}: {e}")
    print(f"\n    This is likely your bug. The error above is what main.py is hitting.")
    import traceback
    traceback.print_exc()

# ── Summary ───────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"  Working model:  {working_model}")
print(f"  Use this in main.py as the first MODEL_FALLBACKS entry.")
print(f"  If Step 6 failed, the image Part construction is the bug —")
print(f"  see the traceback above for the exact fix needed.")