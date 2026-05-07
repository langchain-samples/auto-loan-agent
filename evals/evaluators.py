"""Code and LLM judge evaluators"""

def ground_truth_eval(inputs: dict, outputs: dict, reference_outputs: dict) -> bool:
    return outputs["lending_decision"] == reference_outputs["lending_decision"]

evaluators = [ground_truth_eval]