import streamlit as st
import httpx

from domain.todos import todos_content
from domain.commom import authenticated_page
from config import BASE_API_URL
from icecream import ic

def page_content():
    r_projects = httpx.get(BASE_API_URL + "ticktick/authenticated")
    ic(r_projects.status_code)
    if r_projects.status_code == 200:
        todos_content()

    else:
        r = httpx.get(BASE_API_URL + "ticktick/authenticate")
        redirect_url = r.json()["redirect_url"]
        st.warning("Please authenticate TickTick")
        redirect_button = st.link_button("TickTick redirect", url=redirect_url)
        if not redirect_button:
            st.stop()
        ic("rerunning")
        st.rerun()


def main():
    st.set_page_config(page_title="Todos", page_icon="📋")
    page_content()


if __name__ == "__main__":
    main()
