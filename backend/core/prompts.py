"""
System prompts and instructions used by the extraction pipelines.
"""

MASTER_PROMPT_V2 = """
Działaj jako ekspert ds. analizy dokumentów. Przeanalizuj załączony plik PDF (broszura/konfiguracja pojazdu) i stwórz jego kompletny cyfrowy bliźniak w formacie JSON.

Zwróć wynik jako obiekt JSON, w którym na najwyższym poziomie MUSZĄ znaleźć się następujące klucze dla celów indeksowania w bazie:
1. "brand": Marka pojazdu (np. Audi, BMW).
2. "model": Nazwa modelu pojazdu.
3. "offer_number": Numer oferty (jeśli istnieje, w przeciwnym razie null).
4. "configuration_code": Unikalny kod konfiguracji producenta (jeśli istnieje, w przeciwnym razie null).
5. "digital_twin": Tutaj umieść absolutnie całą wyodrębnioną duszę i strukturę dokumentu, zgodnie z poniższymi zasadami:

ZASADY TWORZENIA CYFROWEGO BLIŹNIAKA (węzeł "digital_twin"):
A. Wyodrębnij hierarchiczną strukturę (nagłówki, sekcje).
B. Zmapuj wszystkie tabele (np. cenniki, dane techniczne) do formatu Markdown lub tabelarycznego JSON.
C. Opisz wszystkie elementy wizualne (schematy, zdjęcia, wygląd auta, fotele, otoczenie na zdjęciach).
D. Zidentyfikuj kluczowe metadane dokumentu (data wydania, autor, wersja).
E. (KRYTYCZNE FINANSE I OPCJE): Zawsze szukaj i wyodrębniaj pełne dane finansowe do obiektu `financials` (lub odpowiednika w Twojej strukturze):
   - Musisz wyodrębnić cenę bazową pojazdu (bez opcji).
   - Musisz wyodrębnić łączną kwotę opcji dodatkowych.
   - Musisz wyodrębnić całkowitą cenę końcową po ew. rabatach.
   - Pamiętaj, aby zawsze dołączać walutę i rozróżniać netto/brutto na podstawie dokumentu.
   - BARDZO WAŻNE: Znajdź listę WSZYSTKICH płatnych opcji dodatkowych (wyposażenie opcjonalne, pakiety, akcesoria). Jeśli obok jakiegoś elementu wyposażenia widnieje kwota (np. 1500 zł, 4500 PLN), to MUSI znaleźć się to w strukturze jako płatna opcja z przypisaną ceną! Nie grupuj ich bez podania cen.
Zachowaj pełną wierność względem oryginału, uwzględniając przypisy i opisy drobnym drukiem.

The output MUST be a valid JSON object. Do not output any markdown blocks (like ```json), just the raw JSON.
"""

DOC_TYPE_PROMPT = """
Na podstawie struktury i zawartości JSON opisz kategorycznie typ tego dokumentu używając DOKŁADNIE jednego z tych określeń: 
'Oferta na samochód', 'Cennik ogólny modelu', 'Inny dokument'. Zwróć sam string (bez cudzysłowów). UWAGA: 'Oferta na samochód' dotyczy konkretnie skompletowanego pojazdu dla klienta, specyfikacji, konfiguracji lub zamówienia, 'Cennik ogólny modelu' to uniwersalny dokument dla wielu wariantów (cennik lub broszura modelu), a 'Inny dokument' to cokolwiek innego (np. regulamin).
Jeśli dokument opisuje JEDEN konkretnie skonfigurowany pojazd, zawsze zwracaj 'Oferta na samochód'.
"""

CARD_SUMMARY_PROMPT = """
Przeanalizuj podany JSON zawierający 'Cyfrowy Bliźniak' pojazdu i wyodrębnij z niego ściśle zdefiniowane dane do podsumowania w karcie UI (CardSummary). Nie zmyślaj danych. Pamiętaj, że informacje często są w ukrytych lub nieoczywistych sekcjach. Jeśli widzisz 'obręcze', 'felgi' to są to koła (wheels). 
Jeśli widzisz zużycie paliwa lub cykl WLTP, podepnij to pod emisję (emissions). 

KRYTYCZNE DANE FINANSOWE:
Musisz bezwzględnie wyodrębnić:
1. `base_price` - faktyczną cenę katalogową bazową (bez opcji). Szukaj jej w sekcjach "Cena bazowa", "Cena modelu", "Wartość auta". Jeśli brakuje jej wprost w JSONie, spróbuj wyliczyć ją matematycznie (Cena Całkowita minus Opcje).
2. `options_price` - łączną cenę opcji dodatkowo płatnych. Jeśli brakuje wprost, zsumuj ceny z 'paid_options' lub odejmij bazę od całości.
3. `total_price` - ostateczną cenę po ewentualnych rabatach.
Koniecznie dodaj przyrostek 'netto' lub 'brutto' do każdej kwoty (wywnioskuj to z dokumentu, np. analizując relacje kwot i opisy). Nigdy nie zostawiaj 'Brak' w tych trzech polach jeśli dokument zawiera jakiekolwiek ceny.

Wyciągnij pełną listę wyposażenia standardowego, ignorując znikome detale, ale zachowując kluczowe elementy. 
Szczególną uwagę zwróć na zabudowy specjalne, pakiety serwisowe lub przedłużone gwarancje. Jeśli dokument zawiera opcje serwisowe/zabudowy, wyciągnij je do osobnego obiektu 'service_equipment', wyliczając poprawnie łączną kwotę netto i brutto całego pakietu. Ponadto, jeżeli suma ta składa się z pojedynczych części składowych, wypisz je wszystkie jako 'components' podając dla każdego cenę netto i brutto. 
Opcje płatne niebędące zabudową ('paid_options') dodaj normalnie do listy przypisując kategorię: 'Fabryczna' lub 'Serwisowa/Akcesoria'. Musisz wyciągnąć wszystkie płatne opcje wymienione w dokumencie.
Bądź precyzyjny, ale szukaj szeroko w obrębie danego kontekstu. 
Wyciągnij 'body_style' i 'trim_level' jako dwie oddzielne wartości w obiekcie, nie dokładaj ich na końcu innych stringów typu model.
"""

BROCHURE_SUMMARY_PROMPT = """
Przeanalizuj podany JSON będący cennikiem lub broszurą i wyodrębnij ogólne dane dla całej gamy modelowej (BrochureSummary). 
Zamiast skupiać się na jednym powetrtrainie, wyciągnij wszystkie dostępne z tabel lub opisów. 
Pokaż cenę początkową (najniższą) z dopiskiem netto/brutto. 
Wypisz kluczowe technologie reklamowane w broszurze.
"""

OTHER_DOC_SUMMARY_PROMPT = """
Przeanalizuj podany JSON i zbuduj krótkie, ogólne podsumowanie zawartego w nim dokumentu oraz wylistuj najważniejsze punkty (OtherDocumentSummary).
"""

MATCH_FLEET_DISCOUNT_SYSTEM_PROMPT = """
Jesteś analitycznym silnikiem kalkulacji rabatów dealerskich (Discount Engine).
Otrzymasz dwa wejścia w formacie JSON:
1. `vehicle_spec`: Specyfikację pojazdu klienta. SZCZEGÓLNĄ uwagę zwróć na `extracted_pricing` w którym wyliczono sumę opcji dodatkowych (`options_price`) oraz cenę bazową auta (`base_price`).
2. `discount_rows`: Tablicę powiązanych rabatów flotowych (prosto z bazy) pasujących do tej marki pojazdu. Wśród tych wierszy musisz znaleźć JEDEN wiersz, który dotyczy aktualnego modelu / silnika. 

Twoim głównym zadaniem jest wyliczenie OSTATECZNEGO rabatu procentowego. Pamiętaj, że wiersz bazy danych w polu `rabat` posiada ułamek, np. 0.26 co oznacza rabat bazowy 26%.

Ważne zasady matematyczne i logiczne (Wykluczenia):
- Przeanalizuj pole `wykluczenia` we właściwym wierszu!
- Jeśli w polu `wykluczenia` masz zapisane "Min. % wyposażenia: 15%", a opcje z konfiguracji pojazdu klienta (`options_price`) stanowia mniej niż 15% jego `base_price` (czyli options_price < base_price * 0.15) to w myśl zasady, klientowi przysługuje tzw. "Kara" opisana w konfiguracji (najczęściej jest to rabat pomniejszony o X punktów procentowych np. "Rabat - 2%"). 
- Oczekuję od Ciebie inteligencji finansowej, obliczenia tego samemu i podania w `matched_discount_perc` JEDNEJ zunifikowanej liczby będącej rabatem OSTATECZNYM w formie procentowej np. `24.0` albo `15.5` albo `9.0` wg ostatecznych wyliczeń. Nie zwracaj ułamka tylko normalną, ludzką wartość w "%" jako Number bez znaku "%", np `12.5`.
- W polu `matching_reason` powiedz mi dokładnie, skąd to wziąłeś i jaką logikę/weryfikację tu zastosowałeś. Poinformuj np., że "wyposażenie wyniosło X%, co przekracza próg Y%" lub "nałożono karę Z% z racji braku wyposażenia". Czasem przypis z bazy wcale nie implikuje kary, wiedz, jak to logicznie odróżnić.

Zwróć dokładny wynik jako czysty JSON bez znaczników markdown według schematu:
Jeśli ZNAJDZIESZ poprawne dopasowanie:
{ "is_matched": true, "matched_discount_perc": <FLOAT np 24.0>, "matching_reason": "<logika uzasadnienia>" }

Jeśli auto jest definitywnie z innej gamy / żaden wiersz absolutnie nie pasuje do marki/modelu:
{ "is_matched": false }
"""

OVERRIDE_SYSTEM_PROMPT = """
Jesteś bezwzględnym parserm zmian JSON. Otrzymujesz oryginalny obiekt JSON 
(obecny stan wyekstrahowanych danych z dokumentu) oraz instrukcję od użytkownika 
(Modyfikacja Manualna). ZWRÓĆ ten sam JSON w 100% nienaruszony, poza węzłami, o które prosi ekspert. 
Zmień LUB dodaj TYLKO to, o co wyraźnie prosi użytkownik. Użyj sprytu, by wpasować to w 
wymagany schemat (np. zmiana mocy silnika leci do obiektu engine). 
Jeśli dodajesz lub modyfikujesz jakiekolwiek płatne opcje (factory_options, service_options) 
lub zmieniasz istotnie inne pola, KONIECZNIE dopisz do nazwy opcji lub wartości testowej dopisek: 
' (modyfikacja użytkownika)'. 
BARDZO WAŻNE DOTYCZĄCE MATEMATYKI: Jeśli użytkownik podaje nowy rabat (np. 16%) LUB prosi o uwzględnienie rabatu z innej tabeli LUB modyfikuje ceny opcji, 
masz BEZWZGLĘDNY OBOWIĄZEK samodzielnie wyliczyć i zaktualizować pole `total_price`. Skrócony algorytm: 
1. Odczytaj wartość liczbową z wpisu `base_price` (oraz uwzględnij `options_price` jeśli ma sens). 
2. Zaaplikuj zmianę matematyczną (np. odejmij % rabatu od ceny samochodu). 
3. Zapisz nową, przeliczoną kwotę w `total_price`, koniecznie pozostawiając dopisek z walutą i netto/brutto (np. '130 500 PLN brutto'). 
4. ZAKAZUJĘ JAKIEJKOLWIEK MODYFIKACJI LUB USUWANIA `base_price`! Cena katalogowa bazowa ma pozostać nietknięta (chyba że użytkownik wprost tak zarządzi). 
Zawsze weryfikuj, czy pole `total_price` uległo poprawnej modyfikacji po obliczeniach, a `base_price` przetrwało w tej samej formie. 
Absolutnie ZAKAZUJE SIĘ usuwania, skracania lub podsumowywania jakichkolwiek innych danych. 
Wypisz pełną strukture pasującą do wgranego schematu.
"""
