"""Create dataset using LangSmith SDK"""

import requests
import uuid
from pathlib import Path
from dotenv import load_dotenv
from langsmith import Client

load_dotenv()
ls_client = Client()

dataset_name = "ds-auto-loan-agent"
dataset_exists = ls_client.list_datasets(dataset_name=dataset_name)

if dataset_exists:

    # PDF URLs
    pdf_urls = {
        "s1": {
            "credit_app": "https://auto-loan-agent-docs-804792415534-us-east-2-an.s3.us-east-2.amazonaws.com/s1_credit_app.pdf",
            "insurance_binder": "https://auto-loan-agent-docs-804792415534-us-east-2-an.s3.us-east-2.amazonaws.com/s1_insurance_binder.pdf",
            "paystub": "https://auto-loan-agent-docs-804792415534-us-east-2-an.s3.us-east-2.amazonaws.com/s1_paystub.pdf",
            "purchase_order": "https://auto-loan-agent-docs-804792415534-us-east-2-an.s3.us-east-2.amazonaws.com/s1_purchase_order.pdf"
        },
        "s2": {
            "credit_app": "https://auto-loan-agent-docs-804792415534-us-east-2-an.s3.us-east-2.amazonaws.com/s2_credit_app.pdf",
            "insurance_binder": "https://auto-loan-agent-docs-804792415534-us-east-2-an.s3.us-east-2.amazonaws.com/s2_insurance_binder.pdf",
            "paystub": "https://auto-loan-agent-docs-804792415534-us-east-2-an.s3.us-east-2.amazonaws.com/s2_paystub.pdf",
            "purchase_order": "https://auto-loan-agent-docs-804792415534-us-east-2-an.s3.us-east-2.amazonaws.com/s2_purchase_order.pdf"
        },
        "s3": {
            "credit_app": "https://auto-loan-agent-docs-804792415534-us-east-2-an.s3.us-east-2.amazonaws.com/s3_credit_app.pdf",
            "insurance_binder": "https://auto-loan-agent-docs-804792415534-us-east-2-an.s3.us-east-2.amazonaws.com/s3_insurance_binder.pdf",
            "paystub": "https://auto-loan-agent-docs-804792415534-us-east-2-an.s3.us-east-2.amazonaws.com/s3_paystub.pdf",
            "purchase_order": "https://auto-loan-agent-docs-804792415534-us-east-2-an.s3.us-east-2.amazonaws.com/s3_purchase_order.pdf"
        },
    }

    # Fetch files as bytes
    pdf_data = {}
    for scenario, urls in pdf_urls.items():
        pdf_data[scenario] = {}
        for doc_type, url in urls.items():
            pdf_data[scenario][doc_type] = requests.get(url).content

    # Create the dataset
    ls_client = Client()
    dataset = ls_client.create_dataset(
        dataset_name = dataset_name,
        description="Eval dataset for auto-loan-agent"
    )

    # Define an example with attachments
    examples = []
    for scenario, docs in pdf_data.items():
        
        if scenario == "s1":
            lending_decision = "HARD_STOP"
        elif scenario == "s2":
            lending_decision = "HARD_STOP"
        else:
            lending_decision = "AUTO_APPROVE"
        
        example = {
            "id": uuid.uuid4(),
            "inputs": {
                "scenario": scenario
            },
            "outputs": {"lending_decision": lending_decision},
            "attachments": {
                "credit_app": {"mime_type": "application/pdf", "data": docs["credit_app"]},
                "insurance_binder": {"mime_type": "application/pdf", "data": docs["insurance_binder"]},
                "paystub": {"mime_type": "application/pdf", "data": docs["paystub"]},
                "purchase_order": {"mime_type": "application/pdf", "data": docs["purchase_order"]}
            }
        }
        examples.append(example)
    
    # Create the example
    ls_client.create_examples(
        dataset_id = dataset.id,
        examples = examples
    )

else:
    print("Dataset already exists")