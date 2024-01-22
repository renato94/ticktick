import streamlit as st
from streamlit_extras.switch_page_button import switch_page
import httpx
from datetime import datetime


def get_title():
    kanye_api = "https://api.kanye.rest/"
    r = httpx.get(kanye_api)
    st.title(str(datetime.now().date()))
    st.write(f"\"{r.json()['quote']}\"")


def main():
    st.set_page_config(page_title="Renato", page_icon="🔥")

    get_title()

    exercise_btn = st.button("➤ Exercise")
    if exercise_btn:
        switch_page("exercise")
    st.divider()
    todo_btn = st.button("➤ Todos")
    if todo_btn:
        switch_page("todos")
    st.divider()

    codgin_btn = st.button("➤ Coding")
    if codgin_btn:
        switch_page("coding")
    st.divider()

    finances_btn = st.button("➤ Finance")
    if finances_btn:
        switch_page("finances")


if __name__ == "__main__":
    main()
