import os
import time
from celery.schedules import crontab
from celery import Celery
from backend.api.github_api import GitHubClient
from backend.config import GITHUB_ACCESS_TOKEN, SQLALCHEMY_DATABASE_URL
import httpx
from icecream import ic
from celery.signals import worker_process_init, worker_process_shutdown
from backend.api import database

celery = Celery(__name__)
celery.conf.broker_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379")
celery.conf.result_backend = os.environ.get(
    "CELERY_RESULT_BACKEND", "redis://localhost:6379"
)


db_conn = None


@worker_process_init.connect
def init_worker(**kwargs):
    global db_conn
    print("Initializing database connection for worker.")
    db_conn = database.get_db(SQLALCHEMY_DATABASE_URL)


@worker_process_shutdown.connect
def shutdown_worker(**kwargs):
    global db_conn
    if db_conn:
        print("Closing database connectionn for worker.")
        db_conn.close()


@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(
        crontab(minute=0, hour="*/3"),  # executes every 3 hours
        get_github_repos.s(),
        expires=10,
    )


@celery.task(name="github_info")
def get_github_repos():
    github_client = GitHubClient(GITHUB_ACCESS_TOKEN)
    repos = github_client.get_repos()
    result = httpx.post("http://localhost:9090/github/repos/set", json=repos)
    ic(result)
    return True
