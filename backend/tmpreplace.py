import os
import re

file_path = r'd:\kalk_v3\backend\core\prompts.py'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if "Jeśli brak informacji, zostaw null." in line and "ILOŚĆ MIEJSC" in "".join(new_lines[-4:]):
        new_lines.append("- Jeśli bezpośrednio nie podano ilości miejsc na ofercie/cenniku, a pojazd to standardowy samochód osobowy (np. Hatchback, Kombi, SUV, Sedan), wydedukuj i przyjmij domyślnie 5 (lub odpowiednio 2/4/7 jeśli to np. roadster lub duży van). W innej sytuacji zostaw null.\n")
    elif "CECHY UŻYTKOWE I WYMIARY (utility_features):" in line:
        new_lines.append("CECHY UŻYTKOWE, TECHNICZNE I WYMIARY (utility_features):\n")
    elif "Znajdź w sekcjach danych technicznych (Technical Data lub w dowolnych tabelach z wymiarami) wszystkie cechy będące liczbami fizycznymi oznaczającymi cechy uzytkowe (głównie samochody dostawcze, chociaż osobowe mogą mieć bagażnik)." in line:
        new_lines.append("Znajdź w sekcjach danych technicznych (Technical Data lub w dowolnych tabelach z wymiarami) wszystkie parametry fizyczne i techniczne pojazdu. ZAKAZ HARDKODOWANIA MAREK I TYPÓW! Dotyczy to KAŻDEGO pojazdu, niezależnie czy to osobówka, czy dostawczak.\n")
        new_lines.append("- Szukaj: mas (masa własna, DMC, dopuszczalna ładowność, masa przyczepy), wymiarów zewnętrznych (długość, szerokość, wysokość, rozstaw osi, prześwit), wymiarów wewnętrznych (pojemność bagażnika w litrach, wymiary paki), a także innych cech mierzalnych.\n")
    elif "Wypisz je wszystkie na listę obiektów zachowując nazwę atrybutu i jego wartość z jednostką (np. \"14.4 m3\", \"3450 mm\"). Bezwzględnie zrób to dla każdego pojazdu klasy dostawczej by dostarczyć parametry do systemu reverse_search. Być odważny i wyciągaj dosłownie każdą użyteczną cechę!" in line:
        new_lines.append("- Wypisz je wszystkie na listę obiektów zachowując oryginalną nazwę atrybutu i jego wartość z jednostką (np. \"400 l\", \"1500 kg\", \"4500 mm\", \"14.4 m3\"). Bądź odważny! Wyciągaj absolutnie każdą fizyczną, mierzalną cechę techniczną z jednostką, jaką tylko znajdziesz w zestawieniach.\n")
    elif "Szukaj słów kluczowych jak: długość paki, ładowność, objętość, rozstaw osi, przestrzen ladunkowa, dopuszczalna masa całkowita (DMC), itp." in line:
        pass # removed
    else:
        new_lines.append(line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Done with script 2")
