import streamlit as st
import httpx
import streamlit_authenticator as stauth
from icecream import ic
import yaml
from yaml.loader import SafeLoader

from config import BASE_API_URL


def page_content():
    r_projects = httpx.get(BASE_API_URL + "authenticated")
    ic(r_projects.status_code)
    if r_projects.status_code == 200:
        projects_data = httpx.get(BASE_API_URL + "tasks").json()
        ic(projects_data)
        st.write(projects_data)
    else:
        r = httpx.get(BASE_API_URL + "authenticate")
        redirect_url = r.json()["redirect_url"]
        st.warning("Please authenticate TickTick")
        redirect_button = st.link_button("TickTick redirect", url=redirect_url)
        if not redirect_button:
            st.stop()
        ic("rerunning")
        st.rerun()


def login_page():
    users_yaml = "app/users.yaml"
    with open(users_yaml) as file:
        config = yaml.load(file, Loader=SafeLoader)

    authenticator = stauth.Authenticate(
        config["credentials"],
        config["cookie"]["name"],
        config["cookie"]["key"],
        config["cookie"]["expiry_days"],
        config["preauthorized"],
    )

    authenticator.login("Login", "main")
    if st.session_state["authentication_status"]:
        authenticator.logout("Logout", "main", key="unique_key")
        page_content()
    elif st.session_state["authentication_status"] is False:
        st.error("Username/password is incorrect")

    elif st.session_state["authentication_status"] is None:
        st.warning("Please enter your username and password")


def main():
    st.set_page_config(page_title="Todos", page_icon="📋")
    login_page()


if __name__ == "__main__":
    main()
