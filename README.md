# Auto Loan Agent

A reference implementation of an auto loan funding agent built on
[LangGraph](https://langchain-ai.github.io/langgraph/) and
[Deep Agents](https://docs.langchain.com/oss/python/deepagents/overview). The
agent ingests a "deal jacket" (credit application, purchase order, paystub,
insurance binder), evaluates the bundle against a funding policy, generates
structured stipulations, and routes a lending decision through a deterministic
policy layer.

This sample is published as a customer-ready starting point: a working
end-to-end pipeline with a Streamlit frontend, a deployable LangGraph backend,
and a fully-wired offline evaluation pipeline against
[LangSmith](https://smith.langchain.com).

## Overview

```
[ Streamlit UI / Eval target ]
            │
            ▼  4 PDFs as base64
[ LangGraph orchestrator ]  ── deterministic policy + action dispatch
            │
            ▼  message + virtual filesystem
[ Deep Agents supervisor ]  ── runs stip checks, emits StipReport
   ├─ deal_jacket_subagent  (extracts structured fields from deal docs)
   └─ policy_subagent       (extracts structured rules from policy doc)
```

Two layers, by design:

1. **LLM reasoning layer** (the deep agent + subagents) handles open-ended
   work: extracting fields from messy PDFs, mapping policy rules, running
   stipulation checks. Outputs are constrained by Pydantic schemas
   (`PolicyCheckOutput`, `DealJacketOutput`, `StipReport`).
2. **Deterministic policy layer** (the orchestrator's tail nodes) handles
   business policy in pure Python: auto-approval rules, action dispatch,
   templated dealer messaging. The schemas form the contract between layers.

The supervisor proposes; the orchestrator decides. This split makes the
auto-approval policy auditable and tunable without prompt engineering.

## What's included

- **LangGraph orchestrator** with five nodes covering input translation, agent
  invocation, deterministic decisioning, action dispatch, and dealer messaging
- **Deep Agents supervisor** with two specialized dict-spec subagents and
  schema-validated structured output
- **Streamlit frontend** with four labeled PDF upload slots and a rendered
  view of the stip report
- **LangSmith offline eval pipeline** with attachment-based dataset support
  and a starter evaluator
- **Mocked downstream APIs** for document requests, underwriter notifications,
  and dealer messaging — easy to replace with real integrations

## Project structure

```
auto-loan-agent/
├── loan_workflow_orchestrator.py   LangGraph state, nodes, graph compile
├── stip_agent.py                    Deep agent factory + subagent specs
├── langgraph.json                   LangGraph deployment config
├── pyproject.toml                   Project dependencies
├── .env.example                     Template for required env vars
├── utils/
│   ├── prompts.py                   System prompts (supervisor + 2 subagents)
│   ├── schemas.py                   Pydantic schemas for all structured outputs
│   └── mock_apis.py                 Mock downstream API responses
├── frontend/
│   ├── app.py                       Streamlit UI
│   └── README.md                    Frontend-specific docs
├── evals/
│   ├── create_dataset.py            One-time script to seed the eval dataset
│   ├── run_experiment.py            Invokes evaluate() against the graph
│   └── evaluators.py                Custom evaluator functions
└── docs/                            Sample deal jacket PDFs (gitignored)
```

## Prerequisites

- Python 3.11 or higher
- [uv](https://docs.astral.sh/uv/) installed
- A [LangSmith](https://smith.langchain.com) account
- An Anthropic API key
- A LangGraph deployment of this project (via LangSmith Deployments). The
  Streamlit UI talks to your deployed endpoint over the LangGraph SDK.

## Setup

This project uses [uv](https://docs.astral.sh/uv/) for dependency
management. Install uv if you don't already have it:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Clone and install dependencies:

```bash
git clone <this-repo>
cd auto-loan-agent
uv sync
```

`uv sync` reads `pyproject.toml` and `uv.lock` to install pinned versions
of every dependency into `.venv/`. No manual venv creation or activation
needed.

Configure environment variables. Copy the example file and fill in your
values:

```bash
cp .env.example .env
```

See `.env.example` for the full list. `LANGGRAPH_URL` is the URL of your
deployment. `LANGGRAPH_ASSISTANT_ID` must match the graph name registered
in `langgraph.json` (default `auto_loan_agent`). The `LANGSMITH_*`
variables enable distributed tracing of agent runs into your workspace.

## Running the Streamlit UI

The frontend is a thin client over your deployed LangGraph agent. With
`.env` configured, launch it via uv:

```bash
uv run streamlit run frontend/app.py
```

The UI opens at <http://localhost:8501>. Upload one PDF into each of the
four labeled slots and click "Run stip analysis". The agent run typically
completes in 30-60 seconds, after which the UI renders the lending
decision, identified issues, triggered stipulations, and final dealer
message. See [frontend/README.md](frontend/README.md) for detail on the
upload contract and configuration knobs.

## Running offline evals

The `evals/` directory contains a fully configured offline evaluation
pipeline against LangSmith. Datasets use LangSmith's
[attachment feature](https://docs.langchain.com/langsmith/evaluate-with-attachments),
so deal jacket PDFs travel with the dataset itself rather than living on
disk at eval time.

### One-time dataset setup

`evals/create_dataset.py` seeds a LangSmith dataset with deal jacket
attachments and reference outputs. Open it, point `DATASET_NAME` and the
scenario list at your test cases, and run:

```bash
uv run python evals/create_dataset.py
```

This creates the dataset shell and uploads each example with its four PDF
attachments. PDFs are read from local fixtures during seeding; you can
delete the local copies afterward (LangSmith holds the canonical copy).

### Running an experiment

`evals/run_experiment.py` defines the target function (which adapts the
dataset's attachment shape to the graph's input contract) and invokes
`evaluate()`:

```bash
uv run python evals/run_experiment.py
```

The script looks the dataset up by name (`dataset_name` constant at the
top of the file). Make sure it matches the name you used in
`create_dataset.py`. Optionally tune `experiment_prefix`, `description`,
and `max_concurrency`.

The experiment posts results to LangSmith, where you can compare runs
side-by-side, inspect agent traces, and track regressions across prompt or
model changes.

### Adding evaluators

`evals/evaluators.py` exposes an `evaluators` list. To add a new check,
write a function with the standard LangSmith evaluator signature and
append it to the list:

```python
def stip_type_coverage(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
    """Fraction of expected stip types that the supervisor identified."""
    actual = {s["type"] for s in outputs["stip_report"]["stips"]}
    expected = set(reference_outputs.get("expected_stip_types") or [])
    if not expected:
        return {"key": "stip_type_coverage", "score": 1.0}
    return {
        "key": "stip_type_coverage",
        "score": len(actual & expected) / len(expected),
    }

evaluators = [ground_truth_eval, stip_type_coverage]
```

The pipeline picks up new evaluators on the next `run_experiment.py`
invocation. Each evaluator's `key` becomes a column in the LangSmith
experiment table.

## Customization

The most common extension points:

| What you want to change | Where to look |
|---|---|
| Auto-approval policy (which stip types auto-approve, max stip count) | `loan_workflow_orchestrator.py` — `AUTO_APPROVABLE_STIPS`, `AUTO_APPROVE_MAX_STIPS` |
| Stipulation checks the supervisor runs | `utils/prompts.py` — `parent_sp` STIP CHECKS section |
| Output schemas (Issue, Stip, StipReport, etc.) | `utils/schemas.py` |
| Subagent prompts | `utils/prompts.py` — `policy_subagent_sp`, `deal_jacket_subagent_sp` |
| Downstream APIs (currently mocked) | `utils/mock_apis.py` |
| Dealer message templates | `loan_workflow_orchestrator.py` — `send_message` |

Adding a new stipulation type typically requires updating the policy
document the agent reads and the supervisor's stip check list. Adding a new
business rule (e.g., a different auto-approval threshold) is a one-file
change in the orchestrator.

## Deployment notes

- The orchestrator does not pass a checkpointer at compile time. LangGraph
  Platform and `langgraph dev` both auto-inject the appropriate checkpointer
  for the runtime, so leave `_builder.compile()` as-is.
- The default supervisor model is set in `stip_agent.py`. Smaller Claude
  models work but with measurably lower reliability on the structured
  output schema; use the eval pipeline to characterize tradeoffs before
  changing.
