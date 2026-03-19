"""Dev server launcher with optimised uvicorn settings for Windows.

Usage:
    poetry run python run_dev.py
"""

from granian import Granian


def main() -> None:
    Granian(
        "main:app",
        address="0.0.0.0",
        port=8000,
        interface="asgi",
        reload=True,
    ).serve()


if __name__ == "__main__":
    main()
