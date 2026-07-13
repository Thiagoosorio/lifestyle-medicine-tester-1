"""Minimal administrator console for account and data-volume verification."""

import pandas as pd
import streamlit as st

from services.admin_service import AdminAccessError, get_account_inventory


st.title("Admin Console")

try:
    inventory = get_account_inventory(st.session_state.user_id)
except AdminAccessError:
    st.error("Administrator access required.")
    st.stop()

metric_columns = st.columns(4)
metric_columns[0].metric("Accounts", inventory["account_count"])
metric_columns[1].metric("Administrators", inventory["admin_count"])
metric_columns[2].metric("User Data Tables", inventory["owned_table_count"])
metric_columns[3].metric("Owned Records", f'{inventory["owned_record_count"]:,}')

st.subheader("Account Inventory")
table_rows = [
    {
        "Username": account["username"],
        "Display Name": account["display_name"] or "",
        "Email": account["email"] or "",
        "Role": account["account_role"].title(),
        "Owned Records": account["owned_records"],
        "Created": account["created_at"],
    }
    for account in inventory["accounts"]
]
st.dataframe(
    pd.DataFrame(table_rows),
    hide_index=True,
    use_container_width=True,
    column_config={
        "Owned Records": st.column_config.NumberColumn(format="%d"),
    },
)
