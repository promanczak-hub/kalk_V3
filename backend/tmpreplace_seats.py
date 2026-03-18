import os

file_path = r'd:\kalk_v3\backend\core\prompts.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """- Jeśli bezpośrednio nie podano ilości miejsc na ofercie/cenniku, a pojazd to standardowy samochód osobowy (np. Hatchback, Kombi, SUV, Sedan), wydedukuj i przyjmij domyślnie 5 (lub odpowiednio 2/4/7 jeśli to np. roadster lub duży van). W innej sytuacji zostaw null."""

replacement = """- Jeśli brak informacji o układzie siedzeń lub ilości miejsc w konfiguracji, cenniku lub innej analizowanej broszurze, bezwzględnie zostaw to pole jako null. Zostanie ono ewentualnie wzbogacone później przy pomocy słowników cech użytkowych."""

new_content = content.replace(target, replacement)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Done replacing number of seats instruction.")
