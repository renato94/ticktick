from functools import lru_cache
from github import Github

from icecream import ic
from github import Auth
from fastapi import APIRouter, Request, Depends

router = APIRouter(prefix="/github", tags=["github"])


class GitHubClient:
    access_token: str = None
    g: Github = None
    user = None
    repos = []

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.g = Github(auth=Auth.Token(access_token))
        self.user = self.get_user()

    @lru_cache
    def get_user(self):
        return self.g.get_user()

    def set_repos(self, repos):
        self.repos = repos

    def get_repo_commits(self, repo):
        ttc = repo.get_commits().totalCount
        commits = []
        if ttc > 30:
            total_pages = (ttc + 30 - 1) // 30
            for i in range(total_pages):
                commits += [c for c in repo.get_commits().get_page(i)]
        else:
            commits = [c for c in repo.get_commits().get_page(0)]

        commits_dict = [
            {
                "name": c.commit.author.name,
                "date": str(c.commit.author.date),
                "message": c.commit.message,
                "size": c.stats.total,
            }
            for c in commits
        ]

        return commits_dict

    def get_repos(self):
        # to be used by celery periodic task
        ic("getting repos")
        raw_repos = self.user.get_repos(affiliation="owner")
        for r in raw_repos:
            self.repos.append(
                {
                    "name": r.full_name,
                    "created_at": str(r.created_at),
                    "description": r.description,
                    "languages": r.get_languages(),
                    "commits": self.get_repo_commits(r),
                }
            )

        ic("got repos")
        return self.repos


def get_github_client(request: Request):
    return request.app.state.github_client


@router.get("/user")
def get_user(g: Github = Depends(get_github_client)):
    user = g.user
    return {
        "name": user.name,
        "avatar_url": user.avatar_url,
        "bio": user.bio,
        "blog": user.blog,
        "created_at": user.created_at,
        "html_url": user.html_url,
    }


@router.post("/repos/set")
async def set_repos(request: Request, g: GitHubClient = Depends(get_github_client)):
    g.set_repos(await request.json())
    return {"success", True}


@router.get("/repos")
def get_repos(g: GitHubClient = Depends(get_github_client)):
    return g.repos


@router.get("/repos/all")
def get_github_repos(request: Request):
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
