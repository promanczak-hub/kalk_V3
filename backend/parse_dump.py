import json

try:
    with open('d:/kalk_v3/backend/ab33_dump.json', 'r', encoding='utf-16') as f:
        text = f.read()

    start = text.find('{')
    end = text.rfind('}') + 1
    if start != -1 and end != -1:
        data = json.loads(text[start:end])
        print("======== CALCULATION TRACE ========")
        for item in data.get('trace', []):
            print(f"{item.get('krok')}: {item.get('rownanie')} = {item.get('wynik')}")
        print("======== TOTALS ========")
        print(f"LacznaStawka: {data.get('LacznaStawka')}")
        print(f"UtrataWartosciZCzynszemInicjalnym: {data.get('UtrataWartosciZCzynszemInicjalnym')}")
        print(f"SumaOdsetekZczynszem: {data.get('SumaOdsetekZczynszem')}")
    else:
        print('No JSON found')
except Exception as e:
    print(f"Error parsing json: {e}")
