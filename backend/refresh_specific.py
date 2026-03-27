import os
import sys

# Dodaj ścieżkę do sys.path, aby można było importować moduły z backendu
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.matrix_cache_job import refresh_matrix_cache_for_vehicles


def main():
    vids = ["CBGM55VH", "CBQDKGWL"]
    print(f"Oświeżanie matrix_cache dla {vids}")
    refresh_matrix_cache_for_vehicles(vids)
    print(
        "Zrobione. Sprawdź backendowe logi w poszukiwaniu ewentualnych wyjątków ValueError."
    )


if __name__ == "__main__":
    main()
