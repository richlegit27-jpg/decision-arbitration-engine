# arbitration_engine.py

from datetime import datetime
import json
from policies import evaluate_policies
from agents import sample_agents
from override import human_override

def arbitrate(agent_reports, override=None, log_file="logs/sample_run.json"):
    """
    Core arbitration engine logic
    """
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "agents": agent_reports,
        "policy_violations": [],
        "final_decision": None
    }

    valid_reports = []

    for report in agent_reports:
        if evaluate_policies(report):
            valid_reports.append(report)
        else:
            log_entry["policy_violations"].append(report["agent_id"])

    if not valid_reports:
        log_entry["final_decision"] = "DENY"
    else:
        recommendations = [r["recommendation"] for r in valid_reports]
        if "DENY" in recommendations:
            log_entry["final_decision"] = "DENY"
        elif "DELAY" in recommendations:
            log_entry["final_decision"] = "DELAY"
        else:
            log_entry["final_decision"] = "ALLOW"

    if override:
        log_entry = human_override(log_entry, **override)

    with open(log_file, "w") as f:
        json.dump(log_entry, f, indent=4)

    return log_entry


if __name__ == "__main__":
    decision = arbitrate(sample_agents)
    print("Decision Log:", decision)
