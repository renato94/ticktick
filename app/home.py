import streamlit as st
from streamlit_extras.switch_page_button import switch_page
from pages.exercise import get_execise_basic_view


def main():
    st.set_page_config(page_title="Renato", page_icon="🔥")

    st.title("Hello, Streamlit!")
    st.write("This is a basic Streamlit application.")

    st.write("Exercise")
    get_execise_basic_view()
    exercise_btn = st.button("Exercise")
    if exercise_btn:
        switch_page("exercise")

    st.write("Todos")
    todo_btn = st.button("Todos")
    if todo_btn:
        switch_page("todos")

    st.write("Coding")
    codgin_btn = st.button("Coding")
    if codgin_btn:
        switch_page("coding")

    st.write("Finance")
    finances_btn = st.button("Finance")
    if finances_btn:
        switch_page("finances")


if __name__ == "__main__":
    main()
