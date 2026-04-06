import json
from core.database import supabase


def main():
    try:
        with open("stats.txt", "w", encoding="utf-8") as f:
            v_res = (
                supabase.table("vehicle_synthesis")
                .select("id, synthesis_data")
                .execute()
            )
            f.write(f"Wszystkich pojazdów: {len(v_res.data)}\n")

            m_res = (
                supabase.table("vehicle_matrix_cache")
                .select(
                    "vehicle_id, duration_months, annual_mileage, monthly_price_net"
                )
                .execute()
            )
            matrix_data = m_res.data or []
            f.write(f"Wszystkich rekordów matrix_cache: {len(matrix_data)}\n")

            # Jak wyglada Skoda Fabia
            fabias = []
            for v in v_res.data:
                sd_str = json.dumps(v.get("synthesis_data", {}))
                if "Skoda" in sd_str and "Fabia" in sd_str:
                    fabias.append(v)
            f.write(f"Znaleziono {len(fabias)} Skod Fabia.\n")

            for fabia in fabias:
                f_id = fabia["id"]
                f_matrices = [m for m in matrix_data if m["vehicle_id"] == f_id]
                f.write(f"Fabia {f_id} -> {len(f_matrices)} wariantow\n")

            # Jakies auto z wariantami
            vehicles_with_matrix = {}
            for m in matrix_data:
                vid = m["vehicle_id"]
                vehicles_with_matrix[vid] = vehicles_with_matrix.get(vid, 0) + 1

            f.write(f"Pojazdy z macierzami: {len(vehicles_with_matrix)}\n")
            for vid, count in list(vehicles_with_matrix.items())[:5]:
                f.write(f"Auto {vid} ma {count} wariantow\n")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
