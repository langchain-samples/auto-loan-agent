# Streamlit Frontend

A lightweight Streamlit UI for the Auto Loan Agent. Provides four labeled
upload slots for the deal jacket documents, calls the deployed LangGraph
agent over the LangSmith SDK, and renders the lending decision, structured
stip report, and dealer message.

This UI is meant to run locally on a developer machine and point at an
already-deployed LangGraph agent. See the [project root README](../README.md)
for the full setup, including environment variables and the offline eval
pipeline.

## Quickstart

From the project root, with `.env` configured and `uv sync` already run
(see the [project root README](../README.md) for full setup):

```bash
uv run streamlit run frontend/app.py
```

The UI opens at <http://localhost:8501>.

## Configuration

These environment variables are read from the project's `.env`:

| Variable | Required | Purpose |
|---|---|---|
| `LANGGRAPH_URL` | yes | URL of your deployed LangGraph endpoint. |
| `LANGGRAPH_ASSISTANT_ID` | optional (default `auto_loan_agent`) | Assistant ID matching `langgraph.json`. |
| `LANGSMITH_API_KEY` | yes | Authenticates SDK calls against the deployment. |

A missing or invalid `LANGSMITH_API_KEY` surfaces as a "Missing
authentication headers" error from the SDK on the first call.

## Using the UI

1. Upload one PDF into each of the four labeled slots: **Credit
   Application**, **Purchase Order**, **Paystub**, **Insurance Binder**.
   PDFs only.
2. Click **Run stip analysis** (becomes enabled once all four are uploaded).
3. Wait 30-60 seconds for the agent run.
4. Review the rendered output:
   - **Lending decision** — colored callout (green for auto-approve, yellow
     for manual review, red for hard stop).
   - **Issues identified** — expandable list of stip checks that fired,
     each with finding, evidence, and policy reference.
   - **Stipulations triggered** — what the dealer must provide to clear
     each stip.
   - **Dealer message** — the templated message the orchestrator would
     send to the dealer.
   - **Raw stip report (debug)** — the full JSON for inspection.

## How it works

1. Each uploaded PDF's bytes are base64-encoded client-side.
2. The frontend creates a fresh thread on the LangGraph deployment and
   invokes the graph with input shaped like:

   ```json
   {
     "messages": [],
     "deal_jacket": {
       "credit_app.pdf": "<base64>",
       "purchase_order.pdf": "<base64>",
       "paystub.pdf": "<base64>",
       "insurance_binder.pdf": "<base64>"
     },
     "files": {}
   }
   ```

3. The orchestrator's `process_jacket` node translates `deal_jacket` into
   the deepagents virtual filesystem under `/docs/`, the supervisor
   delegates to subagents, and the run completes.
4. The frontend reads `lending_decision`, `stip_report`, and the final
   message off the run's final state for rendering.

## File size cap

Inputs are capped at 10 MB per file as a sanity check. The cap lives in
`app.py` as `MAX_BYTES_PER_FILE`. Real deal jacket PDFs in the sample
dataset are ~10 KB; adjust if you need larger documents.
