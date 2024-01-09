from functools import lru_cache
from typing import List
from github import Github

from icecream import ic
from github import Auth
from api.config import GITHUB_ACCESS_TOKEN
from fastapi import APIRouter

router = APIRouter(prefix="/github", tags=["github"])
auth = Auth.Token(GITHUB_ACCESS_TOKEN)
g = Github(auth=auth)
user = g.get_user()


@router.get("/repos")
def get_repos():
    return {
        "n_repos": len([repo for repo in g.get_user().get_repos(affiliation="owner")])
    }


@router.get("/repos/all")
def get_github_repos():
    repos = []
    for repo in g.get_user().get_repos(affiliation="owner"):
        name = repo.name
        activity = repo.get_stats_commit_activity()
        activity = [
            {"week": ac.week, "total": ac.total, "days": ac.days}
            for ac in activity
            if any(ac.days)
        ]
        n_commits = sum([ac["total"] for ac in activity])
        repos.append(
            {
                "name": name,
                "description": repo.description,
                "activity": activity,
                "n_commits": n_commits,
            }
        )

    return repos
