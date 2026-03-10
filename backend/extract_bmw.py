import json


def extract():
    with open("d:/kalk_v3/backend/online_all.json", encoding="utf-8") as f:
        data = json.load(f)

    # Check what brands we actually have
    x3s = []
    for row in data:
        # Check synthesis_data
        syn = row.get("synthesis_data", {})
        if not syn:
            continue

        # Some are just dicts
        dt = syn.get("digital_twin", {})

        # Check brand
        b = syn.get("brand", "")
        if b == "BMW":
            x3s.append(syn)

    with open(
        "d:/kalk_v3/backend/online_bmw_x3_rest2.json", "w", encoding="utf-8"
    ) as f:
        json.dump(x3s, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    extract()
