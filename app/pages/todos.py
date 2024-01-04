import streamlit as st
import httpx
import streamlit_authenticator as stauth

import yaml
from yaml.loader import SafeLoader

st.set_page_config(page_title="Todos", page_icon="📋")

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


def authorise_ticktick():
    r = httpx.get("http://localhost:8000/authenticate")
    st.link_button("Redirect", url=r.json()["redirect_url"])


def add_authenticated_todos():
    st.button("authorise", on_click=authorise_ticktick)


if st.session_state["authentication_status"]:
    authenticator.logout("Logout", "main", key="unique_key")
    add_authenticated_todos()
elif st.session_state["authentication_status"] is False:
    st.error("Username/password is incorrect")

elif st.session_state["authentication_status"] is None:
    st.warning("Please enter your username and password")
