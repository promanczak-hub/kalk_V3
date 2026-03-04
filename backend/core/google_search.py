from duckduckgo_search import DDGS  # type: ignore


def get_service_interval_from_search(
    brand: str, model: str, trim: str, year: str = ""
) -> str:
    """
    Wykonuje wyszukiwanie w internecie za pomocą DuckDuckGo w celu odnalezienia
    informacji o interwale serwisowym dla danego samochodu.
    """
    # Poprawione zapytanie z rygorystycznym filtrem wyników po polskich stronach by pominąć spamerskie sieci botów:
    query = f'"{brand} {model}" {trim} {year} interwał serwisowy OR przegląd OR "co ile km" site:pl'.strip()
    try:
        with DDGS() as ddgs:
            # Używamy regionu pl-pl (backend domyślnie 'api')
            results = list(ddgs.text(query, max_results=5, region="pl-pl"))

            if not results:
                # W przypadku braku wyników w zawężonym przeszukaniu, szukamy elastycznie nadal przy pomocy polskich portali
                fallback_query = (
                    f"{brand} {model} {trim} {year} interwał serwisowy wymiana oleju"
                )
                results = list(
                    ddgs.text(
                        fallback_query, max_results=5, region="pl-pl", backend="lite"
                    )
                )

            if not results:
                return ""

            # Połącz 5 pierwsze wyniki w jeden tekst (context) dla LLM
            context = "\n".join(
                [f"Tytuł: {r.get('title')}\nSnippet: {r.get('body')}" for r in results]
            )
            return context
    except Exception as e:
        print(f"Błąd wyszukiwarki (fallback): {e}")
        return ""
