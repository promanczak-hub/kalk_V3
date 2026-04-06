from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client()

print("Uploading file to Gemini...")
uploaded_file = client.files.upload(
    file=r"C:\Users\proma\Downloads\opisapki.pdf",
    config={"mime_type": "application/pdf"},
)

prompt = """Ten PDF zawiera zrzuty ekranu aplikacji z KOMENTARZAMI / ADNOTACJAMI użytkownika.
Mnie NIE interesuje opis funkcjonalności aplikacji widocznej na screenshotach.

Interesują mnie WYŁĄCZNIE:
1. Komentarze tekstowe użytkownika (np. dymki, notatki, komentarze PDF, tekst nałożony na zrzuty)
2. Strzałki, podkreślenia, zakreślenia — co wskazują i co użytkownik chciał nimi zaznaczyć
3. Wszelkie uwagi, pytania, instrukcje, TODO, sugestie zmian napisane przez użytkownika NA lub OBOK screenshotów
4. Jeśli w dokumencie są odręczne/narysowane notatki — opisz je

Dla KAŻDEGO screenshota/strony:
- Podaj numer strony
- Opisz co DOKŁADNIE użytkownik skomentował / zaznaczył
- Zacytuj tekst komentarza dosłownie (jeśli jest czytelny)
- Opisz kontekst — na CO wskazuje dany komentarz (który element UI)

Odpowiedź w języku polskim. Bądź MAKSYMALNIE szczegółowy — każdy komentarz jest ważny."""

try:
    response = client.models.generate_content(
        model="gemini-2.5-pro", contents=[uploaded_file, prompt]
    )
except Exception as e:
    print(f"Failed with gemini-2.5-pro: {e}, trying 1.5-pro")
    response = client.models.generate_content(
        model="gemini-1.5-pro", contents=[uploaded_file, prompt]
    )

with open("opis_comments.txt", "w", encoding="utf-8") as f:
    f.write(response.text)

print("Done — saved to opis_comments.txt")
