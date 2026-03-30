import json
from google import genai
from google.genai import types

out = dir(types.Part)
with open("test_sdk.json", "w", encoding="utf-8") as f:
    json.dump(out, f)
