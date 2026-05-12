import requests
import json
import base64
from PIL import Image
import io

def test():
    print("Testing Ollama image request with 800x800 image...")
    # Create an 800x800 dummy image
    img = Image.new('RGB', (800, 800), color = 'red')
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    image_bytes = buffer.getvalue()
    b64_image = base64.b64encode(image_bytes).decode('utf-8')
    
    PROMPT = """Analyze this product packaging image carefully.
Identify the product type (food, beverage, cosmetic, supplement, cleaning product, etc.).

Return ONLY a valid JSON object — no markdown, no code fences, no explanation.

{
    "productName": "name from the label",
    "category": "Food | Beverage | Cosmetic | Supplement | Skincare | Household",
    "score": 50,
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

    payload = {
        "model": "llava",
        "prompt": PROMPT,
        "images": [b64_image],
        "stream": False,
        "format": "json"
    }
    try:
        print("Sending request to Ollama...")
        response = requests.post("http://127.0.0.1:11434/api/generate", json=payload, timeout=120)
        response.raise_for_status()
        print("Success!")
        
    except Exception as e:
        print(f"Error: {e}")
        if hasattr(e, 'response') and e.response:
            print(e.response.text)

if __name__ == "__main__":
    test()
