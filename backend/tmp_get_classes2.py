import os
import requests


def main():
    try:
        drafts_res = requests.get(
            os.environ.get("API_URL", "http://127.0.0.1:8000") + "/api/excel-drafts"
        )
        drafts = drafts_res.json()

        old_classes = set()
        for sheet in drafts:
            print(f"Sheet: {sheet['sheet_name']}")
            class_col = None
            for col in sheet.get("columns_def", []):
                if "klasa" in col["headerName"].lower() or col["field"] == "Col_1":
                    class_col = col["field"]
                    print(f"  Found class col: {class_col} ({col['headerName']})")
                    break

            if class_col:
                for row in sheet.get("data_rows", []):
                    val = row.get(class_col)
                    if val and isinstance(val, str):
                        old_classes.add(val)

        print("\n--- OLD CLASSES ---")
        for oc in sorted(list(old_classes)):
            print(oc)

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
