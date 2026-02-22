import streamlit as st
from models.user import create_user, verify_user
from components.custom_theme import APPLE, render_pillar_icons

A = APPLE

# ══════════════════════════════════════════════════════════════════════════════
# LOGIN PAGE — All HTML uses single-line strings (no indentation, no blank lines)
# ══════════════════════════════════════════════════════════════════════════════

# ── Hero Banner ───────────────────────────────────────────────────────────────
hero_html = (
    f'<div style="background:{A["hero_gradient"]};border-radius:{A["radius_2xl"]};'
    f'padding:48px 32px;position:relative;overflow:hidden;margin-bottom:32px;text-align:center">'
    f'<div style="position:absolute;top:-60px;left:-60px;width:300px;height:300px;'
    f'background:radial-gradient(circle,rgba(94,92,230,0.35) 0%,transparent 70%);'
    f'pointer-events:none;border-radius:50%;'
    f'animation:anim-orb-drift 8s ease-in-out infinite alternate"></div>'
    f'<div style="position:absolute;bottom:-80px;right:-40px;width:350px;height:350px;'
    f'background:radial-gradient(circle,rgba(250,45,85,0.20) 0%,transparent 70%);'
    f'pointer-events:none;border-radius:50%;'
    f'animation:anim-orb-drift 10s ease-in-out infinite alternate-reverse"></div>'
    f'<div style="position:relative;z-index:1">'
    f'<div style="font-size:3.5rem;margin-bottom:12px">&#10084;&#65039;</div>'
    f'<div style="font-family:{A["font_display"]};font-size:34px;line-height:41px;'
    f'font-weight:800;color:{A["label_primary"]};letter-spacing:-0.02em;'
    f'margin-bottom:12px">Lifestyle Medicine<br>Coach</div>'
    f'<div style="font-family:{A["font_text"]};font-size:17px;line-height:22px;'
    f'color:{A["label_secondary"]};max-width:420px;margin:0 auto">'
    f'Your evidence-based companion for building healthier habits '
    f'across all 6 pillars of lifestyle medicine.</div>'
    f'</div>'
    f'</div>'
)
st.markdown(hero_html, unsafe_allow_html=True)


# ── Pillar Icons Row ──────────────────────────────────────────────────────────
render_pillar_icons()


# ── Quick Demo Login Banner ───────────────────────────────────────────────────
demo_html = (
    f'<div style="border-radius:{A["radius_lg"]};padding:16px;margin-bottom:24px;'
    f'text-align:center;background:rgba(94,92,230,0.12);'
    f'border:1px solid rgba(94,92,230,0.25)">'
    f'<div style="font-size:11px;font-weight:600;text-transform:uppercase;'
    f'letter-spacing:0.06em;color:{A["indigo"]};margin-bottom:4px">'
    f'&#128640; Try the Demo</div>'
    f'<div style="font-size:13px;color:{A["label_secondary"]}">'
    f'Experience Maria\'s 12-month transformation journey</div>'
    f'</div>'
)
st.markdown(demo_html, unsafe_allow_html=True)

if st.button("Quick Demo Login (maria.silva)", use_container_width=True, type="primary"):
    user = verify_user("maria.silva", "demo123456")
    if user:
        st.session_state.user_id = user["id"]
        st.session_state.display_name = user["display_name"]
        st.rerun()
    else:
        st.error("Demo account not found. Run `python seed_demo.py` first.")

st.markdown("---")


# ── Login / Register Tabs ────────────────────────────────────────────────────
tab_login, tab_register = st.tabs(["Sign In", "Create Account"])

with tab_login:
    with st.form("login_form"):
        username = st.text_input("Username", key="login_username", placeholder="Enter your username")
        password = st.text_input("Password", type="password", key="login_password", placeholder="Enter your password")
        submitted = st.form_submit_button("Sign In", use_container_width=True)
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
        new_username = st.text_input("Choose a username", key="reg_username", placeholder="e.g. john.doe")
        new_display_name = st.text_input("Display name", key="reg_display_name", placeholder="e.g. John Doe")
        new_email = st.text_input("Email (optional)", key="reg_email", placeholder="e.g. john@example.com")
        new_password = st.text_input("Password", type="password", key="reg_password", placeholder="At least 6 characters")
        confirm_password = st.text_input("Confirm password", type="password", key="reg_confirm", placeholder="Re-enter password")
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
                        st.error("Username already taken.")
                    else:
                        st.error(f"Error: {e}")


# ── Footer ────────────────────────────────────────────────────────────────────
footer_html = (
    f'<div style="text-align:center;margin-top:24px;padding:20px 0;'
    f'color:{A["label_quaternary"]};font-size:12px;line-height:16px">'
    f'Built with evidence-based lifestyle medicine principles<br>'
    f'Powered by the 6 ACLM Pillars</div>'
)
st.markdown(footer_html, unsafe_allow_html=True)
