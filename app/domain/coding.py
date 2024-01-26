from datetime import datetime
import httpx
import streamlit as st
from streamlit_card import card
from config import BASE_API_URL
import pandas as pd
import plotly.graph_objects as go
from dateutil import parser
import calendar
import numpy as np
from icecream import ic


def get_github_user():
    r = httpx.get(BASE_API_URL + "github/user")
    return r.json()


def get_github_repos():
    r_repos = httpx.get(BASE_API_URL + "github/repos")
    return r_repos.json()


def plot_current_month_commits(commits_df=None, current_month=None, current_year=None):
    if commits_df is None:
        repos_commits = get_github_repos()
        commits = []
        for repo in repos_commits:
            for commit in repo["commits"]:
                commit["repo"] = repo["name"]
                commits_df = commits.append(commit)
        commits_df = pd.DataFrame(commits)
        commits_df["date"] = pd.to_datetime(commits_df["date"])
    if current_month is None and current_year is None:
        current_month = datetime.now().month
        current_year = datetime.now().year

    commits_df = commits_df[commits_df["date"].dt.year == current_year]
    commits_df = commits_df[commits_df["date"].dt.month == current_month]
    # Get the number of weeks in the current month
    num_weeks = len(calendar.monthcalendar(current_year, current_month))
    ic(num_weeks)
    # Create a list of weekdays
    weekdays = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    # Create a matrix to store the number of commits per weekday and week
    commits_matrix = np.zeros((int(num_weeks), 7))
    # Fill the matrix with the number of commits
    for _, commit in commits_df.iterrows():
        week = int((commit["date"].day - 1) / 7)
        weekday = commit["date"].weekday()
        commits_matrix[week][weekday] += 1
    ic(commits_matrix)

    fig = go.Figure(
        data=go.Heatmap(
            z=commits_matrix,
            x=weekdays,
            y=list(range(1, int(num_weeks) + 1)),
            colorscale="thermal",
            showscale=False,
            xgap=2,
            ygap=3,
        ),
        layout=go.Layout(
            title=f"{calendar.month_name[current_month]} commits",
            xaxis_title="Weekday",
            yaxis_title="Week",
        ),
    )

    st.plotly_chart(fig, use_container_width=True)
