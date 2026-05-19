"""Dev server launcher with optimised uvicorn settings for Windows.

Usage:
    poetry run python run_dev.py
"""

import uvicorn


def main() -> None:
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    main()
