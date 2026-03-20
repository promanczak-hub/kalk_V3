@echo off
echo Uruchamiam workera Celery DEDYKOWANEGO DLA UPLOADOW (Kolejka: uploads)
poetry run celery -A worker worker -Q uploads --pool=solo --loglevel=info
pause
