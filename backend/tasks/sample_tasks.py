from core.celery_app import celery_app
import time


@celery_app.task
def ping_task(word: str) -> str:
    time.sleep(2)
    return f"Pong: {word}"
