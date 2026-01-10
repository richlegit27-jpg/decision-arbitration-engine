# policies.py

def ethics_veto(report):
    """
    Veto high-risk ALLOW actions.
    """
    return not (report["risk"] == "HIGH" and report["recommendation"] == "ALLOW")

POLICIES = [ethics_veto]

def evaluate_policies(report):
    for policy in POLICIES:
        if not policy(report):
            return False
    return True
