from core.matrix_cache_job import refresh_matrix_cache_for_vehicles


def main():
    vehicles = [
        "158e4de0-e3c9-488f-b224-676be5659a5d",
        "a6d6ff54-1dbb-4bb4-905e-71fcc240083a",
    ]

    print("Refreshing cache for octavias...")
    refresh_matrix_cache_for_vehicles(vehicles)
    print("Done")


if __name__ == "__main__":
    main()
