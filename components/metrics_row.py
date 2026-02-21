import streamlit as st


def render_metrics_row(metrics: list[dict]):
    """Render a row of st.metric cards. metrics = [{label, value, delta, help}]."""
    cols = st.columns(len(metrics))
    for i, m in enumerate(metrics):
        with cols[i]:
            st.metric(
                label=m["label"],
                value=m["value"],
                delta=m.get("delta"),
                help=m.get("help"),
            )
