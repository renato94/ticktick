


## Start Server (FastAPI)

uvicorn backend.api.main:app --port 9090 --reload

## Start TaskRunner (Celery)

celery -A backend.celery_t.worker worker --loglevel=info

## Start Beat (Celery beat)

celery -A backend.celery_t beat -l info

## Start Flower (Flower)

celery flower --app:celery_t.celery --broker redis://redis:6379/0