"""Garmin Connect — Import health data from your Garmin wearable."""

import streamlit as st
from components.custom_theme import APPLE, render_hero_banner, render_section_header
from services.garmin_service import (
    connect,
    get_garmin_connection,
    save_garmin_credentials,
    update_last_sync,
    import_sleep_data,
    import_activity_data,
    import_body_composition,
    import_heart_rate,
)

A = APPLE
user_id = st.session_state.user_id

render_hero_banner(
    "Garmin Connect",
    "Import sleep, activity, body composition, and heart rate data from your Garmin device."
)

# Privacy notice
privacy_html = (
    f'<div style="background:{A["bg_elevated"]};border:1px solid {A["teal"]}40;'
    f'border-left:3px solid {A["teal"]};'
    f'border-radius:{A["radius_md"]};padding:12px 16px;margin-bottom:16px">'
    f'<div style="font-size:12px;color:{A["label_secondary"]}">'
    f'&#128274; <strong>Privacy:</strong> Your Garmin credentials are used only for this session. '
    f'No passwords are stored. Data is imported directly to your local database.</div></div>'
)
st.markdown(privacy_html, unsafe_allow_html=True)

connection = get_garmin_connection(user_id)
garmin_client = st.session_state.get("garmin_client")

tab_connect, tab_import = st.tabs(["Connect", "Import Data"])

# ══════════════════════════════════════════════════════════════════════════
# Tab 1: Connect
# ══════════════════════════════════════════════════════════════════════════
with tab_connect:
    render_section_header("Garmin Account", "Sign in to your Garmin Connect account")

    if garmin_client:
        connected_html = (
            f'<div style="background:{A["bg_elevated"]};border:1px solid #30D15840;'
            f'border-radius:{A["radius_md"]};padding:16px;text-align:center">'
            f'<div style="font-size:24px;margin-bottom:8px">&#9989;</div>'
            f'<div style="font-size:15px;font-weight:600;color:#30D158">Connected</div>'
            f'<div style="font-size:12px;color:{A["label_tertiary"]};margin-top:4px">'
            f'{connection["garmin_email"] if connection else "Active session"}</div></div>'
        )
        st.markdown(connected_html, unsafe_allow_html=True)

        if connection and connection.get("last_sync"):
            st.caption(f"Last sync: {connection['last_sync']}")

        if st.button("Disconnect", use_container_width=True):
            st.session_state.pop("garmin_client", None)
            st.rerun()
    else:
        with st.form("garmin_login"):
            email = st.text_input("Garmin Email", value=connection["garmin_email"] if connection else "")
            password = st.text_input("Garmin Password", type="password")

            if st.form_submit_button("Connect to Garmin", use_container_width=True):
                if not email or not password:
                    st.warning("Please enter both email and password.")
                else:
                    with st.spinner("Connecting to Garmin Connect..."):
                        try:
                            client = connect(email, password)
                            st.session_state["garmin_client"] = client
                            save_garmin_credentials(user_id, email)
                            st.toast("Connected to Garmin Connect!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Connection failed: {str(e)}")

# ══════════════════════════════════════════════════════════════════════════
# Tab 2: Import Data
# ══════════════════════════════════════════════════════════════════════════
with tab_import:
    render_section_header("Import Data", "Pull data from Garmin Connect into your trackers")

    if not garmin_client:
        st.info("Connect to your Garmin account first using the **Connect** tab.")
    else:
        days = st.select_slider("Import range (days)", options=[3, 7, 14, 30], value=7)

        import_options = {
            "sleep": {"label": "Sleep Data", "icon": "&#128164;", "desc": "Sleep duration, quality, awakenings", "color": A["purple"]},
            "activity": {"label": "Activity Data", "icon": "&#127939;", "desc": "Steps, active minutes, calories", "color": A["green"]},
            "body": {"label": "Body Composition", "icon": "&#9878;", "desc": "Weight, body fat percentage", "color": A["blue"]},
            "hr": {"label": "Heart Rate", "icon": "&#10084;", "desc": "Resting heart rate as biomarker", "color": A["red"]},
        }

        for key, opt in import_options.items():
            col_info, col_btn = st.columns([3, 1])
            with col_info:
                opt_html = (
                    f'<div style="background:{A["bg_elevated"]};border:1px solid {A["separator"]};'
                    f'border-left:3px solid {opt["color"]};'
                    f'border-radius:{A["radius_md"]};padding:12px 16px">'
                    f'<div style="font-size:14px;font-weight:600;color:{A["label_primary"]}">'
                    f'{opt["icon"]} {opt["label"]}</div>'
                    f'<div style="font-size:11px;color:{A["label_tertiary"]}">{opt["desc"]}</div>'
                    f'</div>'
                )
                st.markdown(opt_html, unsafe_allow_html=True)
            with col_btn:
                st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
                if st.button(f"Import", key=f"import_{key}", use_container_width=True):
                    with st.spinner(f"Importing {opt['label']}..."):
                        try:
                            if key == "sleep":
                                count = import_sleep_data(user_id, garmin_client, days=days)
                            elif key == "activity":
                                count = import_activity_data(user_id, garmin_client, days=days)
                            elif key == "body":
                                count = import_body_composition(user_id, garmin_client, days=days)
                            else:
                                count = import_heart_rate(user_id, garmin_client, days=days)

                            update_last_sync(user_id)
                            st.toast(f"Imported {count} {opt['label'].lower()} records!")
                        except Exception as e:
                            st.error(f"Import failed: {str(e)}")

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

        if st.button("Import All", use_container_width=True, type="primary"):
            results = {}
            with st.spinner("Importing all data from Garmin Connect..."):
                try:
                    results["Sleep"] = import_sleep_data(user_id, garmin_client, days=days)
                except Exception:
                    results["Sleep"] = "Error"
                try:
                    results["Activity"] = import_activity_data(user_id, garmin_client, days=days)
                except Exception:
                    results["Activity"] = "Error"
                try:
                    results["Body"] = import_body_composition(user_id, garmin_client, days=days)
                except Exception:
                    results["Body"] = "Error"
                try:
                    results["Heart Rate"] = import_heart_rate(user_id, garmin_client, days=days)
                except Exception:
                    results["Heart Rate"] = "Error"

                update_last_sync(user_id)

            # Show results
            result_parts = []
            for name, count in results.items():
                if count == "Error":
                    result_parts.append(f'{name}: failed')
                else:
                    result_parts.append(f'{name}: {count} records')

            result_html = (
                f'<div style="background:{A["bg_elevated"]};border:1px solid #30D15840;'
                f'border-radius:{A["radius_md"]};padding:14px 16px;margin-top:8px">'
                f'<div style="font-size:13px;font-weight:600;color:#30D158;margin-bottom:6px">'
                f'&#9989; Import Complete</div>'
                f'<div style="font-size:12px;color:{A["label_secondary"]}">'
                f'{" &nbsp;&middot;&nbsp; ".join(result_parts)}</div></div>'
            )
            st.markdown(result_html, unsafe_allow_html=True)
