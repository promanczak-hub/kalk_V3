from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client()

print("Uploading file to Gemini...")
uploaded_file = client.files.upload(
    file=r"C:\Users\proma\Downloads\opisapki.pdf",
    config={"mime_type": "application/pdf"},
)

print("Asking Gemini to extract and formalize features...")
prompt = "Proszę wyodrębnij i opisz wszystkie funkcjonalności oraz założenia techniczne i biznesowe tej aplikacji zapisane w dokumencie PDF. Zostaw w języku polskim."

# Depending on quota, gemini-2.5-pro or gemini-1.5-pro might be available
try:
    response = client.models.generate_content(
        model="gemini-2.5-pro", contents=[uploaded_file, prompt]
    )
except Exception as e:
    print(f"Failed with gemini-2.5-pro: {e}, trying 1.5-pro")
    response = client.models.generate_content(
        model="gemini-1.5-pro", contents=[uploaded_file, prompt]
    )

with open("opis_summary.txt", "w", encoding="utf-8") as f:
    f.write(response.text)

print("Done")
