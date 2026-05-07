from pydantic import BaseModel, Field
from typing import Literal

# Subagent Output Schemas
class PolicyRule(BaseModel):
    article: str = Field(description="Article and section reference, e.g. 'Article 3.3(b)'")
    rule_name: str = Field(description="Short name for the check, e.g. 'Income Variance Limit'")
    description: str = Field(description="Plain-language description of what the rule requires")
    fields_to_compare: list[str] = Field(description="Snake_case field names from the deal jacket this rule applies to")
    threshold: str = Field(description="Required value or threshold, e.g. '10.0% maximum variance', '$1,000.00 maximum'")
    hard_stop: bool = Field(description="Whether a violation is an immediate hard stop with no cure path")
    stip_triggered: str = Field(description="Name of the stipulation triggered on violation")

class PolicyCheckOutput(BaseModel):
    policy_document: str = Field(description="Source policy document filename")
    policy_version: str = Field(description="Version of the policy document, if stated")
    rules: list[PolicyRule] = Field(description="All extracted policy rules relevant to funding checks")


class ExtractedField(BaseModel):
    field_name: str = Field(description="Standardized snake_case field name, e.g. 'applicant_name', 'vin', 'deductible_amount'")
    raw_value: str = Field(description="Exact value as it appears in the document")
    normalized_value: str = Field(description="Value normalized for comparison (numbers stripped of formatting, VINs/names uppercased, dates as ISO 8601)")
    source_document: str = Field(description="Filename of the source document")
    confidence: Literal["high", "medium", "low"] = Field(description="Extraction confidence level")

class DealJacketOutput(BaseModel):
    documents_processed: list[str] = Field(description="Filenames of all documents that were read")
    fields: list[ExtractedField] = Field(description="All structured fields extracted across all deal jacket documents")
    extraction_notes: list[str] = Field(description="Notes on missing values, ambiguities, or extraction issues")

# Supervisor Output Schemas
class Issue(BaseModel):
    check: str = Field(description="Name of the stip check that produced this issue (e.g. 'Income Variance', 'VIN Consistency')")
    finding: str = Field(description="Plain-language description of what was found")
    evidence: str = Field(description="Exact values from the documents, with calculations shown")
    policy_reference: str = Field(description="Article and section reference, e.g. 'Article 3.3(b)'")

class Stip(BaseModel):
    type: str = Field(description="Stipulation type, e.g. 'Proof of Income', 'Corrected Insurance Binder', 'Deductible Adjustment', 'Loss Payee Correction', 'One and the Same Affidavit'")
    description: str = Field(description="What the dealer must provide to clear this stip")
    triggered_by: str = Field(description="Name of the check that triggered this stip")

class Action(BaseModel):
    action: str = Field(description="Next action to take, e.g. 'request_document', 'notify_underwriter', 'send_dealer_email'")
    details: str = Field(description="Specifics needed to perform the action")

class StipReport(BaseModel):
    deal_id: str = Field(description="Thread or file identifier for this deal")
    issues: list[Issue] = Field(description="All stip-check issues found during analysis")
    stips: list[Stip] = Field(description="All stipulations triggered by the issues")
    actions: list[Action] = Field(description="Next actions for the orchestrator to invoke")
    lending_recommendation: Literal["APPROVE_WITH_STIPS", "HARD_STOP", "CLEAR_TO_FUND"] = Field(
        description="Final lending recommendation based on the issues and stips found"
    )