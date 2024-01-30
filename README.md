# ticktick

## Start Server (FastAPI)

uvicorn backend.api.main:app --port 9090 --reload

## Start TaskRunner (Celery)

celery -A backend.celery_t.worker worker --loglevel=info

## Start Beat (Celery beat)

celery -A backend.celery_t.worker  beat -l info

## Start Flower (Flower)

celery flower -A backend.celery_t.worker --broker redis://localhost:6379/0

## Start StreamLit

streamlit run --server.headless True app/🏠-home.py