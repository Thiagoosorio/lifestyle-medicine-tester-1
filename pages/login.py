import streamlit as st
from models.user import create_user, verify_user


st.title("Welcome to Lifestyle Medicine Coach")
st.markdown("Your evidence-based companion for building healthier habits across all 6 pillars of lifestyle medicine.")

tab_login, tab_register = st.tabs(["Login", "Register"])

with tab_login:
    with st.form("login_form"):
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        submitted = st.form_submit_button("Login", use_container_width=True)
        if submitted:
            if not username or not password:
                st.error("Please enter both username and password.")
            else:
                user = verify_user(username, password)
                if user:
                    st.session_state.user_id = user["id"]
                    st.session_state.display_name = user["display_name"]
                    st.rerun()
                else:
                    st.error("Invalid username or password.")

with tab_register:
    with st.form("register_form"):
        new_username = st.text_input("Choose a username", key="reg_username")
        new_display_name = st.text_input("Display name", key="reg_display_name")
        new_email = st.text_input("Email (optional)", key="reg_email")
        new_password = st.text_input("Password", type="password", key="reg_password")
        confirm_password = st.text_input("Confirm password", type="password", key="reg_confirm")
        reg_submitted = st.form_submit_button("Create Account", use_container_width=True)
        if reg_submitted:
            if not new_username or not new_password:
                st.error("Username and password are required.")
            elif len(new_password) < 6:
                st.error("Password must be at least 6 characters.")
            elif new_password != confirm_password:
                st.error("Passwords do not match.")
            else:
                try:
                    user_id = create_user(new_username, new_password, new_display_name, new_email)
                    st.session_state.user_id = user_id
                    st.session_state.display_name = new_display_name or new_username
                    st.success("Account created! Redirecting...")
                    st.rerun()
                except Exception as e:
                    if "UNIQUE constraint" in str(e):
                        st.error("Username already taken. Please choose another.")
                    else:
                        st.error(f"Error creating account: {e}")
