from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import os
import io
import base64
import json
import logging

# We will try to import google-genai, but if API key is not set, we will use mock data
try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None

app = FastAPI(title="NutriTracker API")

# Setup static files directory
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to initialize Gemini client
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = None
if GEMINI_API_KEY and genai:
    client = genai.Client(api_key=GEMINI_API_KEY)

@app.get("/", response_class=HTMLResponse)
async def read_index():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/api/analyze")
async def analyze_image(image: UploadFile = File(...)):
    """
    Receives an image and calls the Gemini API to analyze ingredients,
    score the product, and verify any claims.
    """
    try:
        content = await image.read()
        
        if client:
            # Prepare file for Gemini
            model_id = "gemini-2.5-pro"
            
            prompt = f"""
            Analyze this product packaging image carefully. First, define what type of product it is (e.g., food, beverage, cosmetic, supplement, cleaning product).
            1. Identify the product name and its category. If the product name is not visible, just return "Product".
            2. Extract the full ingredients list. Determine if each ingredient is generally good, bad, or neutral for this specific type of product.
            3. Extract any specific nutritional, health, or performance claims made on the packaging.
            4. Verify those claims based strictly on the ingredients present.
            5. Provide an overall health/safety score out of 100 based on its chemical/ingredient composition.
            
            Return the output STRICTLY as a JSON object with this exact structure:
            {{
                "productName": "string",
                "category": "string",
                "score": integer_between_0_and_100,
                "ingredients": [
                    {{
                        "name": "string",
                        "status": "good" | "bad" | "neutral",
                        "reason": "detailed explanation (2-3 sentences) detailing its purpose in the product, any potential health impacts or side-effects, and why it received this status."
                    }}
                ],
                "claims": [
                    {{
                        "claim": "string",
                        "isReal": boolean,
                        "explanation": "detailed breakdown (2-3 sentences) of exactly why this claim is true, false, or misleading, specifically naming the ingredients that prove or contradict it."
                    }}
                ]
            }}
            """
            
            # Using inline data for the content
            part = types.Part.from_bytes(data=content, mime_type=image.content_type)
            
            response = client.models.generate_content(
                model=model_id,
                contents=[prompt, part],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                )
            )
            
            result = json.loads(response.text)
            return JSONResponse(content=result)

        else:
            # MOCK RESPONSE (No API key provided)
            # This demonstrates the application logic while waiting for user setup
            logger.warning("No Gemini API key found. Using mock response.")
            mock_data = {
                "productName": "Product",
                "category": "Household/Food/Cosmetic",
                "score": 45,
                "ingredients": [
                    {"name": "Water / Aqua", "status": "neutral", "reason": "Acts as a primary base solvent to dissolve other ingredients and provide the necessary consistency. Because it is chemically inert, it poses no health risks and is completely neutral in this formulation."},
                    {"name": "Artificial Fragrance or Flavor", "status": "bad", "reason": "Often acts as an umbrella term for hundreds of undisclosed synthetic chemicals. These unlisted compounds can frequently cause skin irritation and are known allergens for sensitive individuals."},
                    {"name": "Sodium Lauryl Sulfate or Sugar", "status": "bad", "reason": "Can be a harsh surfactant that strips natural oils leading to dryness in cosmetics, or when found in foods, contributes to rapid spikes in blood glucose levels. Its inclusion signifies a less premium or harsher formulation."},
                    {"name": "Aloe Vera / Whole Oat", "status": "good", "reason": "Rich in antioxidants, vitamins, and natural anti-inflammatory compounds. It actively soothes the targeted area, promotes healing, and adds genuine nutritional or dermatological value to the product."}
                ],
                "claims": [
                    {"claim": "100% All Natural", "isReal": False, "explanation": "This claim is highly misleading. The product contains 'Artificial Fragrance', which is synthesized in a lab and directly contradicts the definition of a 100% natural product. Do not trust this label."},
                    {"claim": "Made with Real Ingredients", "isReal": True, "explanation": "This claim is technically accurate as the formulation incorporates genuine Aloe Vera and Whole Oat extracts. However, it is used as a marketing halo to distract from the artificial additives also present."}
                ]
            }
            return JSONResponse(content=mock_data)

    except Exception as e:
        logger.error(f"Error analyzing image: {str(e)}")
        return JSONResponse(content={"error": str(e)}, status_code=500)
