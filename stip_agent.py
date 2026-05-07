"""
Deep Agents-based stip generation agent. 
"""

from dotenv import load_dotenv
from deepagents import create_deep_agent

from utils.prompts import parent_sp, policy_subagent_sp, deal_jacket_subagent_sp
from utils.schemas import PolicyCheckOutput, DealJacketOutput, StipReport

load_dotenv()

# ============================================================================
# Backend Config
# ============================================================================

# ============================================================================
# Tools
# ============================================================================

# ============================================================================
# Subagents
# ============================================================================
policy_subagent = {
    "name": "policy_subagent",
    "description": "Reads funding policy documents and returns structured policy rules that the supervisor uses to evaluate the deal jacket.",
    "system_prompt": policy_subagent_sp,
    "response_format": PolicyCheckOutput,
}

deal_jacket_subagent = {
    "name": "deal_jacket_subagent",
    "description": "Reads all deal jacket documents (credit app, purchase order, paystub, insurance binder) and returns every extracted field as structured data.",
    "system_prompt": deal_jacket_subagent_sp,
    "response_format": DealJacketOutput,
}

# ============================================================================
# Instantiate Deep Agent
# ============================================================================
agent = create_deep_agent(
    model="anthropic:claude-sonnet-4-6",
    subagents=[policy_subagent, deal_jacket_subagent],
    system_prompt=parent_sp,
    response_format=StipReport
)