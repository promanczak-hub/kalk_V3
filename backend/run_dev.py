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
        reload_dirs=["./"],
        reload_excludes=[
            "__pycache__",
            "*.pyc",
            "*.log",
            "tests/*",
            "*.txt",
            ".git/*",
        ],
        timeout_keep_alive=30,
    )


if __name__ == "__main__":
    main()
