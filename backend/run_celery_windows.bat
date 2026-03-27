@echo off
echo Uruchamiam GŁÓWNEGO workera Celery (z wymuszeniem --pool=solo dla Windowsa)
poetry run python -m celery -A core.celery_app worker -Q celery --pool=solo --loglevel=info
pause
