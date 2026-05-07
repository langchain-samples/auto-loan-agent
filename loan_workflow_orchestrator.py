"""
LangGraph orchestration workflow for an auto loan funding use case.
"""

from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, START
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage
from dotenv import load_dotenv
import uuid
import pathlib
import base64

from utils.schemas import StipReport
from stip_agent import agent
from utils.mock_apis import notify_dealer, send_document_request, notify_underwriter

load_dotenv()

# ============================================================================
# Constants
# ============================================================================
AUTO_APPROVABLE_STIPS = {
    "Proof of Income",
    "Deductible Adjustment",
}
AUTO_APPROVE_MAX_STIPS = 2

# ============================================================================
# Static assets
# ============================================================================

DOCS_DIR = pathlib.Path(__file__).parent / "docs"

def _load_static_files() -> dict:
    """Load files that are immutable across all deals (just the policy for now)."""
    pdf = (DOCS_DIR / "funding_policies.pdf").read_bytes()
    return {
        "/docs/funding_policies.pdf": {
            "content": base64.b64encode(pdf).decode(),
            "encoding": "base64",
        }
    }

STATIC_FILES = _load_static_files()

# ============================================================================
# State
# ============================================================================

class State(TypedDict):
    messages: Annotated[list, add_messages]
    deal_jacket: dict[str, str] # Input (from Streamlit or local FS)
    files: dict[str, dict] # Output (what we send to Deep Agent in proper format)
    stip_report: StipReport
    lending_decision: str

# ============================================================================
# Node Functions
# ============================================================================

def process_jacket(state: State) -> dict:
    """Translate uploaded deal jacket docs into deepagents expected format"""
    
    # Create a dict with path and b64 encoded data from state
    files = {
        f"/docs/{filename}": {"content": b64, "encoding": "base64"}
        for filename, b64 in state["deal_jacket"].items()
    }
    return {"files": files}

def generate_stip(state: State) -> dict:
    """Builds message for deep agent invocation and passes files"""
    
    deal_id = str(uuid.uuid4())
    files = {**STATIC_FILES, **state["files"]}

    instruction = (
        f"Deal ID: {deal_id}. The deal jacket and funding policy live in "
        f"the agent filesystem under /docs/. Delegate to deal_jacket_subagent "
        f"and policy_subagent, then produce the stip report."
    )

    print(f"⚙️  Auto loan agent is processing deal {deal_id[:8]}...")

    # invoke deep agent
    result = agent.invoke(
        {"messages": [HumanMessage(content=instruction)], "files": files},
        config={"configurable": {"thread_id": deal_id}}
    )
    return {
        "messages": [result["messages"][-1]],
        "stip_report": result["structured_response"]
    }

def make_lending_decision(state: State) -> dict:
    """Deterministic rule based checks based on constants for lending decision"""
    report = state["stip_report"]
    
    if report.lending_recommendation == "HARD_STOP":
        decision = "HARD_STOP"
    elif not report.stips:
        decision = "AUTO_APPROVE"
    elif (len(report.stips) <= AUTO_APPROVE_MAX_STIPS
            and all(s.type in AUTO_APPROVABLE_STIPS for s in report.stips)):
        decision = "AUTO_APPROVE_WITH_STIPS"
    else:
        decision = "MANUAL_REVIEW"
    
    return {"lending_decision": decision}

def invoke_stip_actions(state: State):
    """Invoke downstream API calls based on the lending decision."""
    
    decision = state["lending_decision"]
    report = state["stip_report"]

    if decision == "AUTO_APPROVE_WITH_STIPS":
        for stip in report.stips:
            print(f"[mock API] request_document for '{stip.type}' → {send_document_request()}")
    elif decision in {"MANUAL_REVIEW", "HARD_STOP"}:
        print(f"[mock API] notify_underwriter for deal {report.deal_id} "
              f"({decision}) → {notify_underwriter()}")

    return {}

def send_message(state: State) -> dict:
    """Templated message that gets sent async to dealers"""
    report = state["stip_report"]
    decision = state["lending_decision"]

    if decision == "AUTO_APPROVE":
        body = "Approved and clear to fund. No outstanding stipulations."
    elif decision == "AUTO_APPROVE_WITH_STIPS":
        stip_lines = "\n".join(f"  - {s.type}: {s.description}" for s in report.stips)
        body = f"Conditionally approved. The following stipulations have been auto-dispatched to the dealer:\n{stip_lines}"
    elif decision == "MANUAL_REVIEW":
        stip_lines = "\n".join(f"  - {s.type}: {s.description}" for s in report.stips)
        body = f"Routed to manual underwriter review. Outstanding stipulations:\n{stip_lines}"
    else:
        issue_lines = "\n".join(f"  - {i.check}: {i.finding}" for i in report.issues)
        body = f"Cannot fund. Hard stop conditions present:\n{issue_lines}"

    message = f"Deal {report.deal_id} — {body}"
    notify_dealer()
    return {"messages": [AIMessage(content=message)]}

# ============================================================================
# Graph Definition
# ============================================================================

_builder = StateGraph(State)

_builder.add_node("process_jacket", process_jacket)
_builder.add_node("generate_stip", generate_stip)
_builder.add_node("make_lending_decision", make_lending_decision)
_builder.add_node("invoke_stip_actions", invoke_stip_actions)
_builder.add_node("send_message", send_message)


_builder.add_edge(START, "process_jacket")
_builder.add_edge("process_jacket", "generate_stip")
_builder.add_edge("generate_stip", "make_lending_decision")
_builder.add_edge("make_lending_decision", "invoke_stip_actions")
_builder.add_edge("invoke_stip_actions", "send_message")
# _builder.add_conditional_edges("router", tools_condition)

graph = _builder.compile()

# ============================================================================
# Local test function + main
# ============================================================================

def _local_test_input() -> dict:
    """Build a graph input dict from local /docs PDFs.
    Mirrors what the Streamlit UI will produce from st.file_uploader bytes."""
    jacket = {}
    for name in ["credit_app.pdf", "purchase_order.pdf", "paystub.pdf", "insurance_binder.pdf"]:
        jacket[name] = base64.b64encode((DOCS_DIR / name).read_bytes()).decode()
    return {"messages": [], "deal_jacket": jacket, "files": {}}

if __name__ == "__main__":
    result = graph.invoke(
        _local_test_input(),
        config={"configurable": {"thread_id": str(uuid.uuid4())}}
    )
    print(result["messages"][-1].content)