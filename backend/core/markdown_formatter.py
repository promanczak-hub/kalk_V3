"""Module for reformatting extracted Markdown using Gemini Flash."""

import logging
from google.genai import types
from core.gemini_client import get_gemini_client, SAFETY_SETTINGS_PERMISSIVE

logger = logging.getLogger(__name__)


def format_markdown_with_llm(raw_markdown: str) -> str:
    """Passes raw Markdown through Gemini Flash to restore structural elements like lists."""
    if not raw_markdown or len(raw_markdown.strip()) == 0:
        return raw_markdown

    try:
        client = get_gemini_client()

        prompt = (
            "Jesteś profesjonalnym asystentem formatowania Markdown. Twoim zadaniem jest przekształcić "
            "poniższy surowy tekst (wyciągnięty z PDF, który zgubił wizualne wypunktowania) "
            "na czysty, poprawny Markdown o doskonałej strukturze.\n"
            "Instrukcje:\n"
            "1. Rozpoznaj listy wyposażenia, opcji czy cech (np. linie oddzielone enterami, które wymieniają cechy) i dodaj im poprawne znaczniki list (np. `- `).\n"
            "2. Zachowaj oryginalne nagłówki (`#`, `##`, statystyki itp.).\n"
            "3. NIE HALUCYNUJ, nie zmieniaj wartości liczbowych, nie ucinaj tekstu i nie dodawaj informacji spoza źródła.\n"
            "4. Zwróć WYŁĄCZNIE sformatowany Markdown, bez żadnych wstępów, komentarzy czy tagów w stylu ```markdown.\n"
            "\n---\nSurowy tekst:\n"
            f"{raw_markdown}"
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.0,
                safety_settings=SAFETY_SETTINGS_PERMISSIVE,
            ),
        )

        if response and response.text:
            text = response.text.strip()
            # Remove markdown code block markers if the model ignored instruction #4
            if text.startswith("```markdown"):
                text = text[11:].strip()
            if text.startswith("```"):
                text = text[3:].strip()
            if text.endswith("```"):
                text = text[:-3].strip()
            return text

        return raw_markdown

    except Exception as e:
        logger.error(f"Error formatting markdown with LLM: {e}")
        return raw_markdown
