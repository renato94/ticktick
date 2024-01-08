from github import Github

from icecream import ic
from github import Auth
from config import GITHUB_ACCESS_TOKEN

# using an access token
auth = Auth.Token(GITHUB_ACCESS_TOKEN)

# Public Web Github
g = Github(auth=auth)

user = g.get_user()
ic(user)

for repo in g.get_user().get_repos(affiliation="owner"):
    ic(repo.name)
    ic(repo.get_commits().totalCount)
