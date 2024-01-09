from git import Commit
from github import Github

from icecream import ic
from github import Auth
from api.config import GITHUB_ACCESS_TOKEN
from fastapi import APIRouter
from github import PaginatedList

router = APIRouter(prefix="/github", tags=["github"])
auth = Auth.Token(GITHUB_ACCESS_TOKEN)
g = Github(auth=auth)
user = g.get_user()


@router.get("/repos")
def get_github_repos():
    repos = []
    for repo in g.get_user().get_repos(affiliation="owner"):
        name = repo.name
        n_commits = repo.get_commits().totalCount
        description = repo.description
        repos.append({"name": name, "n_commits": n_commits, "description": description})

    return repos
