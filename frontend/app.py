"""Streamlit frontend for the auto loan stip generation demo.

Provides four labeled upload slots for the deal jacket documents and invokes
the deployed LangGraph agent via the LangGraph SDK. Renders the resulting
lending decision, stip report, and final dealer message.

Run locally:
    1. Start the LangGraph dev server from the project root:  langgraph dev
    2. In a separate shell, from the project root:            streamlit run frontend/app.py
"""

import base64
import os

import streamlit as st
from dotenv import load_dotenv
from langgraph_sdk import get_sync_client

load_dotenv()

# ============================================================================
# Configuration
# ============================================================================

LANGGRAPH_URL = os.getenv("LANGGRAPH_URL", "http://localhost:2024")
ASSISTANT_ID = os.getenv("LANGGRAPH_ASSISTANT_ID", "auto_loan_agent")

# Sanity cap so a misuploaded huge file doesn't blow out memory before we even hit the agent.
# Real deal jacket PDFs are ~10 KB; 10 MB is a generous ceiling.
MAX_BYTES_PER_FILE = 10 * 1024 * 1024

# The four canonical document slots. Label is what the user sees;
# the second value is the canonical filename the orchestrator and prompts expect.
DOC_SLOTS = [
    ("Credit Application", "credit_app.pdf"),
    ("Purchase Order", "purchase_order.pdf"),
    ("Paystub", "paystub.pdf"),
    ("Insurance Binder", "insurance_binder.pdf"),
]


# ============================================================================
# Backend communication
# ============================================================================

def _build_deal_jacket(uploads: dict) -> dict:
    """Convert {canonical_filename: UploadedFile} into {canonical_filename: base64_str}.

    Mirrors the shape the orchestrator's process_jacket node expects.
    """
    return {
        filename: base64.b64encode(upload.getvalue()).decode()
        for filename, upload in uploads.items()
    }


def _run_agent(deal_jacket: dict) -> dict:
    """Invoke the deployed agent over the LangGraph SDK and return the final state."""
    api_key = os.getenv("LANGSMITH_API_KEY")
    client = get_sync_client(url=LANGGRAPH_URL, api_key=api_key)
    thread = client.threads.create()

    input_state = {"messages": [], "deal_jacket": deal_jacket, "files": {}}

    final_state: dict = {}
    for chunk in client.runs.stream(
        thread_id=thread["thread_id"],
        assistant_id=ASSISTANT_ID,
        input=input_state,
        stream_mode="values",
    ):
        if chunk.event == "values":
            final_state = chunk.data
    return final_state


# ============================================================================
# Render helpers
# ============================================================================

def _render_decision(decision: str | None) -> None:
    if decision == "AUTO_APPROVE":
        st.success(f"**{decision}** — clean deal, funding cleared")
    elif decision == "AUTO_APPROVE_WITH_STIPS":
        st.success(f"**{decision}** — funding cleared, stipulation requests auto-dispatched")
    elif decision == "MANUAL_REVIEW":
        st.warning(f"**{decision}** — routed to underwriter")
    elif decision == "HARD_STOP":
        st.error(f"**{decision}** — cannot fund")
    else:
        st.info(f"**{decision or 'UNKNOWN'}**")


def _render_report(report: dict | None) -> None:
    if not report:
        return

    if report.get("issues"):
        st.subheader("Issues identified")
        for issue in report["issues"]:
            with st.expander(f"{issue['check']} — {issue['policy_reference']}"):
                st.markdown(f"**Finding:** {issue['finding']}")
                st.markdown(f"**Evidence:** {issue['evidence']}")

    if report.get("stips"):
        st.subheader("Stipulations triggered")
        for stip in report["stips"]:
            st.markdown(
                f"- **{stip['type']}** *(from {stip['triggered_by']})*: {stip['description']}"
            )

    with st.expander("Raw stip report (debug)"):
        st.json(report)


def _render_dealer_message(messages: list) -> None:
    if not messages:
        return
    last = messages[-1]
    content = last.get("content") if isinstance(last, dict) else getattr(last, "content", "")
    if not content:
        return
    st.subheader("Dealer message")
    st.code(content, language=None)


# ============================================================================
# Main
# ============================================================================

def main() -> None:
    st.set_page_config(page_title="Auto Loan Stip Agent", layout="wide")
    st.title("Auto Loan Stipulation Agent")
    st.markdown(
        "Upload the four deal jacket documents below. The agent extracts structured "
        "fields, evaluates them against the funding policy, and produces a stip "
        "report with a lending decision."
    )

    # Upload grid (2x2)
    uploads: dict = {}
    oversize: list[str] = []
    cols = st.columns(2)
    for i, (label, canonical_name) in enumerate(DOC_SLOTS):
        with cols[i % 2]:
            uploaded = st.file_uploader(
                label=label,
                type=["pdf"],
                key=canonical_name,
            )
            if uploaded is None:
                continue
            if uploaded.size > MAX_BYTES_PER_FILE:
                oversize.append(label)
                continue
            uploads[canonical_name] = uploaded

    if oversize:
        st.error(
            f"File too large (max {MAX_BYTES_PER_FILE // (1024*1024)} MB): "
            + ", ".join(oversize)
        )

    all_uploaded = len(uploads) == len(DOC_SLOTS) and not oversize
    if not all_uploaded and not oversize:
        missing = [label for label, name in DOC_SLOTS if name not in uploads]
        st.info("Waiting on: " + ", ".join(missing))

    if st.button("Run stip analysis", disabled=not all_uploaded, type="primary"):
        with st.status("Running stip pipeline…", expanded=True) as status:
            st.write("Encoding documents…")
            deal_jacket = _build_deal_jacket(uploads)
            st.write(f"Invoking LangGraph agent at `{LANGGRAPH_URL}` (30–60s)…")
            try:
                final_state = _run_agent(deal_jacket)
                status.update(label="Stip analysis complete", state="complete")
            except Exception as exc:
                status.update(label=f"Run failed: {exc}", state="error")
                st.exception(exc)
                return

        st.divider()
        st.subheader("Lending decision")
        _render_decision(final_state.get("lending_decision"))

        _render_report(final_state.get("stip_report"))

        _render_dealer_message(final_state.get("messages") or [])


if __name__ == "__main__":
    main()
