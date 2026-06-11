import os
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
print(f"Brand New API Key: {api_key[:10]}...{api_key[-5:] if api_key else ''}")

try:
    from google import genai
    client = genai.Client(api_key=api_key)
    print("Listing models using new google-genai:")
    for m in client.models.list():
        print(f" - {m.name}")
except Exception as e:
    print(f"Error listing models: {e}")
