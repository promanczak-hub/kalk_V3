from core.matrix_cache_job import process_single_kalkulacja_matrix_task
import traceback


def main():
    fabia_id = "3ec82f6d-1b43-4967-b511-8bfd65266fcc"
    print(f"Testowowanie Fabii: {fabia_id}")
    try:
        # matrix tasks are synchronous actually in core/matrix_cache_job.py
        process_single_kalkulacja_matrix_task(fabia_id)
        print("Done!")
    except Exception as e:
        print(f"Wyjatek: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()
