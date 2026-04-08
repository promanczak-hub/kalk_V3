@echo off
echo Uruchamiam workera Celery DEDYKOWANEGO DLA UPLOADOW (Kolejka: uploads)
poetry run python -m celery -A core.celery_app worker -Q uploads --pool=threads --concurrency=10 --loglevel=info
pause
