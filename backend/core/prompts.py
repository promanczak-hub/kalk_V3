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

SZTYWNA KATEGORYZACJA SILNIKA I MOCY (Enum):
Musisz wyciągnąć informacje o układzie napędowym, mocy oraz zasilaniu i dokonać kategoryzacji. 
Przyporządkuj zmienną `engine_category` do JEDNEJ z poniższych wartości (nie modyfikuj stringów!):
- "Benzyna (PB) (Konwencjonalne (ICE))"
- "Diesel (ON) (Konwencjonalne (ICE))"
- "Benzyna mHEV (PB-mHEV) (Miękkie Hybrydy (mHEV))"
- "Diesel mHEV (ON-mHEV) (Miękkie Hybrydy (mHEV))"
- "Hybryda (HEV)"
- "Hybryda Plug-in (PHEV)"
- "Elektryczny (BEV)"

Moc silnika (np. 150 KM) wpisz wpisz do zmiennej `power_hp`.
Następnie przyporządkuj zmienną `power_range` do JEDNEJ z poniższych wartości (nie modyfikuj stringów!):
- "LOW (do 130 KM)"
- "MID (131 - 200 KM)"
- "HIGH (201 KM i więcej)"

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
Jesteś obiektywnym skryptem wybierającym rabat z bazy danych zniżek. Twoim celem jest ZNALEZIENIE I ZWRÓCENIE poprawnej wartości przypisanego rabatu (kolumna `rabat`) bez wprowadzania "własnej matematyki".

Otrzymasz dwa wejścia w formacie JSON:
1. `vehicle_spec`: Specyfikacja pojazdu.
2. `discount_rows`: Tablica wierszy zniżek z bazy pobrana względem marki. Znajdź wśród nich JEDEN wiersz, który dotyczy opisanego modelu / silnika. 

Zasady:
- Przeanalizuj pole `wykluczenia` we właściwym wierszu! Jeśli z opcji w pliku wynika "kara", tj. wyposażenie klienta stanowi mniej niż X% wartości samochodu, oblicz karę i odejmij ją od rabatu bazowego w wierszu. 
- Nie zgaduj "rabatu" na podstawie matematyki w ofercie! Masz obowiązek oprzeć ostateczną liczbę wyłącznie o kolumnę `rabat` z przypisanego wiersza. Przekonwertuj liczbę zmiennoprzecinkową np. `0.24` na ludzką `24.0` (lub 0.27 na 27.0).
- SZALENIE WAŻNE: Bądź elastyczny w kwestii skrótów typu "FL" (Facelift), "NG" (New Generation), "Combi" vs "Kombi" czy wielkość liter. 
- ZWRÓĆ UWAGĘ NA NADWOZIE: LLM ma samodzielnie zdecydować, do którego rabatu przypisać dany samochód na podstawie specyfikacji. Jeśli auto w ofercie to konkretne nadwozie (np. "Avant", "Limousine", "Sportback"), dopasuj wiersz rabatu odpowiadający temu nadwoziu.
- SZALENIE WAŻNE: Jeśli model z oferty (np. "Karoq") pojawia się w polu `model` w bazie (np. "Karoq, Kodiaq" lub "Wszystkie modele"), MUSISZ uznać to za dopasowanie! 
- Zawsze wybieraj najbardziej szczegółowo dopasowany wiersz (np. dopasowanie po nazwie modelu i nadwoziu jest lepsze niż dopasowanie ogólne).

Zwróć dokładny wynik jako czysty JSON bez znaczników markdown według schematu:
Jeśli ZNAJDZIESZ poprawne dopasowanie:
{ "is_matched": true, "matched_discount_perc": <FLOAT np 24.0>, "matching_reason": "<logika uzasadnienia>" }

Jeśli auto jest definitywnie z innej gamy względem dostarczonych wierszy z bazy:
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
