import streamlit as st
from email_validator import validate_email, EmailNotValidError
from icecream import ic


def validate_email_format(email):
    try:
        emailinfo = validate_email(email, check_deliverability=True)
        email = emailinfo.normalized
        return True
    except EmailNotValidError as e:
        ic(e)
        # The exception message is human-readable explanation of why it's
        # not a valid (or deliverable) email address.
        return False


def main():
    st.set_page_config(page_title="About", page_icon="🔥", layout="wide")

    st.link_button(
        "Linkedin", url="https://www.linkedin.com/in/renato-mendes-pinheiro/"
    )

    valid_form = False
    with st.form("my_form"):
        name_value = st.text_input("Name")
        email_value = st.text_input("Email")
        occupation_value = st.text_input("occupation")

        # Every form must have a submit button.
        submitted = st.form_submit_button(
            "Submit", on_click=validate_email_format, args=(email_value,)
        )
        ic(submitted)
        if submitted:
            valid_email = validate_email_format(email_value)
            valid_name = name_value != ""
            valid_occupation = occupation_value != ""
            valid_form = valid_email and valid_name and valid_occupation
            if valid_form:
                st.success("Form submitted")
            else:
                st.error("Invalid form")
    if valid_form:
        st.download_button(
            "Download resume",
            data="app/CV-2022.pdf",
            file_name="Renato Mendes Pinheiro.pdf",
        )


if __name__ == "__main__":
    main()
