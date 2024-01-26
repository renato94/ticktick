import streamlit_authenticator as stauth
from icecream import ic
import yaml
from yaml.loader import SafeLoader
import streamlit as st


def authenticated_page(page_content):
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
