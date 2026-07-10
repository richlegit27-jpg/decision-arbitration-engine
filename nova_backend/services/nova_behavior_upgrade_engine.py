"""
NOVA CONVERSATION BEHAVIOR UPGRADE ENGINE

Turns conversation quality evaluation signals into
actionable behavior improvements.
"""

from dataclasses import dataclass, asdict


@dataclass
class BehaviorUpgrade:
    behavior_problem: str
    severity: str
    upgrade: str
    action: str
    reason: str

    def as_dict(self):
        return asdict(self)


def _severity(score):
    if score < 50:
        return "critical"

    if score < 75:
        return "high"

    if score < 90:
        return "medium"

    return "low"


def analyze_behavior_upgrade(
    evaluation
):
    """
    Accepts either:
    - evaluator object with as_dict()
    - dictionary
    """

    if hasattr(evaluation, "as_dict"):
        data = evaluation.as_dict()
    else:
        data = evaluation or {}

    issues = data.get("issues", [])

    continuity = data.get(
        "continuity",
        100
    )

    helpfulness = data.get(
        "helpfulness",
        100
    )

    reasoning = data.get(
        "reasoning",
        100
    )

    actionability = data.get(
        "actionability",
        100
    )


    issue_text = " ".join(
        str(x).lower()
        for x in issues
    )

    if data.get(
        "user_correction",
        False
    ):
        return BehaviorUpgrade(
            behavior_problem="user_correction_received",
            severity="high",
            upgrade="improve_target_interpretation_before_answering",
            action="detect_user_intent_correction_and_realign_context",
            reason="The user corrected Nova's understanding of the requested target."
        )


    if (
        continuity < 75
        or "context" in issue_text
        or "continuity" in issue_text
    ):
        return BehaviorUpgrade(
            behavior_problem="continuity_failure",
            severity=_severity(continuity),
            upgrade="prioritize_available_context_before_generic_response",
            action="lookup_project_state_and_previous_conversation_context",
            reason="The user likely expected continuation but context handling was weak."
        )


    if (
        helpfulness < 75
        or "short" in issue_text
        or "brief" in issue_text
    ):
        return BehaviorUpgrade(
            behavior_problem="low_helpfulness_depth",
            severity=_severity(helpfulness),
            upgrade="increase_solution_depth_and_next_steps",
            action="expand_answer_with_reasoning_and_action_plan",
            reason="The response may be correct but not useful enough."
        )


    if reasoning < 75:
        return BehaviorUpgrade(
            behavior_problem="weak_reasoning",
            severity=_severity(reasoning),
            upgrade="improve_internal_problem_breakdown",
            action="decompose_problem_before_answering",
            reason="The response needs stronger analysis."
        )


    if actionability < 75:
        return BehaviorUpgrade(
            behavior_problem="weak_actionability",
            severity=_severity(actionability),
            upgrade="provide_clear_execution_path",
            action="include_specific_next_command_or_step",
            reason="The user needs a clearer way forward."
        )


    return BehaviorUpgrade(
        behavior_problem="no_major_behavior_issue",
        severity="low",
        upgrade="continue_collecting_real_conversations",
        action="observe_more_behavior_data",
        reason="Current behavior signals do not show a major failure."
    )


def create_behavior_card(evaluation):
    upgrade = analyze_behavior_upgrade(evaluation)

    return {
        "title": "Nova Behavior Upgrade",
        "recommended_move": upgrade.upgrade,
        "severity": upgrade.severity,
        "problem": upgrade.behavior_problem,
        "exact_next_action": upgrade.action,
        "reason": upgrade.reason,
    }