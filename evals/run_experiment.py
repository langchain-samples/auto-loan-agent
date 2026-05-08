"""Script to run experiment with evals"""

import uuid
import base64
from langsmith import Client
from dotenv import load_dotenv

from evaluators import evaluators
from loan_workflow_orchestrator import graph

load_dotenv()

ls_client = Client()
# Dataset is looked up by name; create_dataset.py uses the same name.
dataset_name = "ds-auto-loan-agent"

# function that we pass into evaluate() that takes in dataset args
def experiment_agent_function(inputs: dict, attachments: dict) -> dict:
    deal_jacket = {
        "credit_app.pdf":       base64.b64encode(attachments["credit_app"]["reader"].read()).decode(),
        "insurance_binder.pdf": base64.b64encode(attachments["insurance_binder"]["reader"].read()).decode(),
        "paystub.pdf":          base64.b64encode(attachments["paystub"]["reader"].read()).decode(),
        "purchase_order.pdf":   base64.b64encode(attachments["purchase_order"]["reader"].read()).decode(),
    }

    # schema that langgraph expects
    graph_input = {
        "messages": [],
        "deal_jacket": deal_jacket,
        "files": {}
    }

    result = graph.invoke(
        graph_input,
        config={"configurable": {"thread_id": str(uuid.uuid4())}}
    )
    
    # return the last message from state
    return {
        "final_message": result["messages"][-1].content,
        "lending_decision": result["lending_decision"],
        "stip_report": result["stip_report"],
    }

results = ls_client.evaluate(
    experiment_agent_function,
    data=dataset_name,
    evaluators = evaluators,
    experiment_prefix="Base Case - Sonnet",
    description="Auto loan application scenarios #1-3 -> Sonnet",
    # max_concurrency=4,
    # metadata=""
)