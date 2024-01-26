import streamlit as st
from streamlit_extras.switch_page_button import switch_page
import httpx
from datetime import datetime
from domain.todos import todos_summary

from domain.exercise import show_current_month_activities
from domain.coding import plot_current_month_commits


def get_title():
    kanye_api = "https://api.kanye.rest/"
    r = httpx.get(kanye_api)
    st.title(str(datetime.now().date()))
    st.write(f"\"{r.json()['quote']}\"\n - Kanye West")


def main():
    st.set_page_config(page_title="Renato", page_icon="🔥", layout="wide")

    get_title()

    exercise_btn = st.button("➤ Exercise")
    show_current_month_activities()
    if exercise_btn:
        switch_page("exercise")
    st.divider()
    todo_btn = st.button("➤ Todos")
    todos_summary()
    if todo_btn:
        switch_page("todos")
    st.divider()

    codgin_btn = st.button("➤ Coding")
    plot_current_month_commits()

    if codgin_btn:
        switch_page("coding")
    st.divider()

    finances_btn = st.button("➤ Finance")
    if finances_btn:
        switch_page("finances")


if __name__ == "__main__":
    main()
