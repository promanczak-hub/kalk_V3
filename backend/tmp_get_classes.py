import os
import requests


def main():
    try:
        samar_classes_res = requests.get(
            os.environ.get("API_URL", "http://127.0.0.1:8000") + "/api/samar-classes"
        )
        samar_classes = [c["name"] for c in samar_classes_res.json()]
    except Exception as e:
        print(f"Error getting samar classes: {e}")
        samar_classes = []

    try:
        drafts_res = requests.get(
            os.environ.get("API_URL", "http://127.0.0.1:8000") + "/api/excel-drafts"
        )
        drafts = drafts_res.json()
    except Exception as e:
        print(f"Error getting excel drafts: {e}")
        drafts = []

    old_classes = set()
    for sheet in drafts:
        # Check if it has a class column
        is_class_sheet = False
        class_col_field = None
        for col in sheet.get("columns_def", []):
            if "klasa" in col["headerName"].lower() or col["field"] == "Col_1":
                is_class_sheet = True
                class_col_field = col["field"]
                break

        if is_class_sheet and class_col_field:
            for row in sheet.get("data_rows", []):
                val = row.get(class_col_field)
                if val and isinstance(val, str):
                    old_classes.add(val)

    print("--- OLD CLASSES IN EXCEL DRAFTS ---")
    for oc in sorted(list(old_classes)):
        print(oc)

    print("\n--- NEW SAMAR CLASSES ---")
    for sc in samar_classes:
        print(sc)


if __name__ == "__main__":
    main()
