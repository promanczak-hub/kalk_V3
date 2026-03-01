from typing import Optional, Tuple


def map_to_samar_class(
    brand: str, model: str, segment: Optional[str], body_style: Optional[str]
) -> Tuple[str, str]:
    """
    Krzyżowe mapowanie z atrybutów pojazdu na (kod_klasy_wr, nazwa_klasy_samar)
    Funkcja zastępuje odgadywanie LLM.
    """
    brand = brand.lower() if brand else ""
    model = model.lower() if model else ""
    segment = segment.lower() if segment else ""
    body = body_style.lower() if body_style else ""

    # Simple heuristic dictionary approach
    # 1. Direct model matches (highest priority)
    # 2. Segment + Body style

    # Przykłady bezpośrednie (z list SAMAR_MARKDOWN):
    if "superb" in model:
        return ("D", "Klasa D ŚREDNIA")
    if "giulia" in model:
        return ("D", "Klasa D ŚREDNIA")
    if "q7" in model or "x5" in model or "gle" in model:
        return ("Esuv", "Klasa E WYŻSZA (Terenowo-Rekreacyjne)")
    if (
        "q5" in model
        or "x3" in model
        or "glc" in model
        or "stelvio" in model
        or "kodiaq" in model
    ):
        return ("Dsuv", "Klasa D ŚREDNIA (Terenowo-Rekreacyjne)")
    if (
        "q3" in model
        or "x1" in model
        or "gla" in model
        or "karoq" in model
        or "tiguan" in model
    ):
        return ("Csuv", "Klasa C NIŻSZA ŚREDNIA (Terenowo-Rekreacyjne)")
    if "octavia" in model or "golf" in model or "corolla" in model or "leon" in model:
        return ("C", "Klasa C NIŻSZA ŚREDNIA")
    if "fabia" in model or "polo" in model or "yaris" in model or "clio" in model:
        return ("B", "Klasa B MAŁE")

    # Fallback based on segments
    if "suv" in body or "crossover" in body or "terenow" in body:
        if "c" in segment:
            return ("Csuv", "Klasa C NIŻSZA ŚREDNIA (Terenowo-Rekreacyjne)")
        if "d" in segment:
            return ("Dsuv", "Klasa D ŚREDNIA (Terenowo-Rekreacyjne)")
        if "e" in segment:
            return ("Esuv", "Klasa E WYŻSZA (Terenowo-Rekreacyjne)")
        if "b" in segment:
            return ("Bsuv", "Klasa B MAŁE (Terenowo-Rekreacyjne)")
        return ("Csuv", "Klasa C NIŻSZA ŚREDNIA (Terenowo-Rekreacyjne)")  # fallback

    if "van" in body or "minivan" in body:
        if "c" in segment:
            return ("Cvan", "Klasa C MINIVANY")
        if "d" in segment:
            return ("Dvan", "Klasa D VANY")
        if "b" in segment:
            return ("Bvan", "Klasa B MICROVANY")
        return ("Cvan", "Klasa C MINIVANY")

    if "a" in segment:
        return ("A", "Klasa A MINI")
    if "b" in segment:
        return ("B", "Klasa B MAŁE")
    if "c" in segment:
        return ("C", "Klasa C NIŻSZA ŚREDNIA")
    if "d" in segment:
        return ("D", "Klasa D ŚREDNIA")
    if "e" in segment:
        return ("E", "Klasa E WYŻSZA")
    if "f" in segment:
        return ("F", "Klasa F LUKSUSOWE")

    # Gdy nic nie pasuje:
    return ("UNKNOWN", "INNE - WYMAGA RĘCZNEGO MAPOWANIA")
