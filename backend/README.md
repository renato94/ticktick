


## Start Server (FastAPI)

uvicorn backend.api.main:app --port 9090 --reload

## Start TaskRunner (Celery)

celery -A backend.celery.worker worker --loglevel=info

## Start Beat (Celery beat)

celery -A backend.celery beat -l info

## Start Flower (Flower)

celery flower --app:backend.celery --broker redis://redis:6379/0