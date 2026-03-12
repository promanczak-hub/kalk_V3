import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    api_key = os.getenv("GOOGLE_API_KEY")

try:
    print("Testing connection to Gemini 2.5 Pro...")
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents="Szybki test łączności. Odpowiedz tylko słowem OK.",
    )
    print("Response:", response.text)
except Exception as e:
    print("Error:", e)
