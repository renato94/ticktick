import os
import time
from celery.schedules import crontab
from celery import Celery
from backend.api.github_api import GitHubClient
from backend.config import GITHUB_ACCESS_TOKEN
import httpx
from icecream import ic

celery = Celery(__name__)
celery.conf.broker_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379")
celery.conf.result_backend = os.environ.get(
    "CELERY_RESULT_BACKEND", "redis://localhost:6379"
)


@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Calls test('world') every 30 seconds
    # sender.add_periodic_task(5.0, periodic_task.s(), expires=10)
    sender.add_periodic_task(10, get_github_repos.s(), expires=10)


@celery.task(name="periodic_task")
def periodic_task():
    time.sleep(2)
    return True


@celery.task(name="github_info")
def get_github_repos():
    github_client = GitHubClient(GITHUB_ACCESS_TOKEN)
    repos = github_client.get_repos()
    result = httpx.post("http://localhost:9090/github/repos/set", json=repos)
    ic(result)
    return True
