import json
import re


def slugify(text):
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "_", text)
    return text.strip("_")


def determine_type(col_name):
    lower_col = col_name.lower()

    # Explicit enums with slash-separated options
    if "(" in lower_col and ")" in lower_col:
        options_str = re.search(r"\((.*?)\)", lower_col)
        if options_str:
            options = options_str.group(1).split("/")
            if len(options) == 2 and set(options) == {"tak", "nie"}:
                return "boolean", None
            elif len(options) > 1:
                return "enum", [o.strip() for o in options]

    # Numeric indicators
    numeric_keywords = [
        " w mm",
        " w kg",
        " w m3",
        " w litrach",
        "liczba",
        "ilość",
        "pojemność",
        "zużycie",
        "zasięg",
    ]
    if any(kw in lower_col for kw in numeric_keywords):
        return "numeric", None

    return "text", None


def main():
    try:
        with open("d:\\kalk_v3\\excel_info.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        columns = data["columns"]

        features = []
        for col in columns:
            if col in ["vin", "nr rej", "nr kontraktu", "Klasa"]:
                continue  # Skip metadata columns

            clean_name = col.split("\n")[0].strip()
            feature_key = slugify(clean_name)

            f_type, options = determine_type(col)

            feature = {
                "display_name": clean_name,
                "feature_key": feature_key,
                "feature_type": f_type,
                "options": options,
                "original_column": col,
            }
            features.append(feature)

        with open("d:\\kalk_v3\\parsed_features.json", "w", encoding="utf-8") as f:
            json.dump(features, f, ensure_ascii=False, indent=2)

        print(f"Successfully parsed {len(features)} features.")

        # Print summary
        counts = {"boolean": 0, "numeric": 0, "enum": 0, "text": 0}
        for f in features:
            counts[f["feature_type"]] += 1

        print("\nType distribution:")
        for k, v in counts.items():
            print(f"- {k}: {v}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
