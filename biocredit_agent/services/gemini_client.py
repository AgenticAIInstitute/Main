import os
from typing import Optional
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

class GeminiClient:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.is_configured = False
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel("gemini-1.5-flash")
                self.is_configured = True
            except Exception as e:
                print(f"Failed to configure Gemini API: {e}")

    def generate_text(self, prompt: str, fallback_text: str = "") -> str:
        if not self.is_configured:
            return fallback_text
            
        try:
            response = self.model.generate_content(prompt)
            if response.text:
                return response.text.strip()
            return fallback_text
        except Exception as e:
            print(f"Gemini API Error: {e}")
            return fallback_text

gemini_client = GeminiClient()
