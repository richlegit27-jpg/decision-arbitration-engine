# override.py
from datetime import datetime

def human_override(log_entry, action, reason, operator):
    """
    Apply a human override on the final decision
    """
    override_record = {
        "operator": operator,
        "action": action,
        "reason": reason,
        "timestamp": datetime.utcnow().isoformat()
    }

    log_entry["human_override"] = override_record
    log_entry["final_decision"] = action
    return log_entry
