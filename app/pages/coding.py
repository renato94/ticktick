import httpx
import streamlit as st
from streamlit_card import card
from config import BASE_API_URL
import pandas as pd
import plotly.graph_objects as go
from dateutil import parser
import calendar

repos = None


def plot_repositories_language(repos):
    repos_languages = {}
    for repo in repos:
        for lang in repo["languages"]:
            if lang in repos_languages.keys():
                repos_languages[lang] += 1
            else:
                repos_languages[lang] = 0

    # filter out  languages with less than 2 repos
    repos_languages = {k: v for k, v in repos_languages.items() if v > 2}
    fig = go.Figure(
        data=[
            go.Pie(
                labels=list(repos_languages.keys()),
                values=list(repos_languages.values()),
            )
        ],
        layout=go.Layout(
            title="Languages used in my repositories",
            showlegend=False,
        ),
    )
    st.plotly_chart(fig)


def get_github_user():
    r = httpx.get(BASE_API_URL + "github/user")
    return r.json()


def get_github_repos():
    r_repos = httpx.get(BASE_API_URL + "github/repos")
    return r_repos.json()


def main():
    st.set_page_config(page_title="coding", page_icon="💻", layout="wide")
    user = get_github_user()
    col1, col2 = st.columns([1, 1])

    with col1:
        card(
            title=user["name"],
            text=user["bio"],
            image=user["avatar_url"],
            url=user["html_url"],
        )
    with col2:
        repos_commits = get_github_repos()
        plot_repositories_language(repos_commits)

    # create a df with every commit and repository it belongs to
    commits = []
    for repo in repos_commits:
        for commit in repo["commits"]:
            commit["repo"] = repo["name"]
            commits_df = commits.append(commit)
    commits_df = pd.DataFrame(commits)
    first_commit = commits_df["date"].min()
    last_commit = commits_df["date"].max()

    col1, col2 = st.columns([1, 1])
    with col1:
        st.metric("First commit", str(parser.parse(first_commit).date()))
    with col2:
        st.metric("Last commit", str(parser.parse(last_commit).date()))

    all_years = list(
        range(parser.parse(first_commit).year, parser.parse(last_commit).year + 1)
    )
    months = list(range(1, 13))

    year_option = st.selectbox("Year", all_years)
    month_option = st.selectbox("Month", months)

    commits_df["date"] = pd.to_datetime(commits_df["date"])
    filtered_commits = commits_df[commits_df["date"].dt.year == year_option]
    filtered_commits = filtered_commits[
        filtered_commits["date"].dt.month == month_option
    ]
    st.dataframe(filtered_commits, use_container_width=True)

    commits_per_month = (
        commits_df.groupby([commits_df["date"].dt.year, commits_df["date"].dt.month])
        .size()
        .unstack(fill_value=0)
    )
    fig = go.Figure(
        data=go.Heatmap(
            z=commits_per_month.values,
            x=[calendar.month_name[c] for c in commits_per_month.columns],
            y=commits_per_month.index,
            colorscale="thermal",
        )
    )
    fig.update_layout(
        title="Number of Commits per Month", xaxis_title="Month", yaxis_title="Year"
    )
    st.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    main()
