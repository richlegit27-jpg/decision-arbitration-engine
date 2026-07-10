from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class ConversationQualityScore:
    overall_score: int
    continuity: int
    helpfulness: int
    reasoning: int
    actionability: int
    issues: list[str]
    strengths: list[str]
    recommended_upgrade: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _contains_any(text: str, values: list[str]) -> bool:
    lowered = text.lower()
    return any(item in lowered for item in values)


def evaluate_conversation(
    user_message: str = "",
    assistant_message: str = "",
    previous_context: str = "",
) -> ConversationQualityScore:
    user = _clean(user_message).lower()
    assistant = _clean(assistant_message).lower()
    context = _clean(previous_context).lower()

    issues: list[str] = []
    strengths: list[str] = []

    continuity = 100
    helpfulness = 100
    reasoning = 100
    actionability = 100

    if _contains_any(
        user,
        [
            "remember",
            "yesterday",
            "earlier",
            "we built",
            "continue",
        ],
    ):
        if not context:
            continuity -= 25
            issues.append(
                "User requested continuity but no previous context was available."
            )
        else:
            strengths.append(
                "Conversation continuity context was available."
            )

    if len(assistant) < 40:
        helpfulness -= 20
        issues.append(
            "Assistant response was too short to be highly useful."
        )

    if _contains_any(
        assistant,
        [
            "i don't know",
            "cannot help",
            "can't help",
            "not possible",
        ],
    ):
        helpfulness -= 15
        issues.append(
            "Assistant gave a limiting response instead of exploring solutions."
        )

    if _contains_any(
        assistant,
        [
            "step 1",
            "first",
            "next",
            "plan",
            "approach",
        ],
    ):
        reasoning += 5
        strengths.append(
            "Assistant provided structured reasoning or planning."
        )

    if _contains_any(
        assistant,
        [
            "create",
            "edit",
            "change",
            "implement",
            "run",
            "test",
        ],
    ):
        actionability += 5
        strengths.append(
            "Assistant provided actionable direction."
        )

    overall = round(
        (
            continuity
            + helpfulness
            + reasoning
            + actionability
        )
        / 4
    )

    if overall >= 85:
        recommended_upgrade = (
            "Continue collecting real conversations before changing behavior."
        )
    elif continuity < helpfulness:
        recommended_upgrade = (
            "Improve conversation memory and continuation handling."
        )
    elif actionability < reasoning:
        recommended_upgrade = (
            "Improve execution guidance and next-step clarity."
        )
    else:
        recommended_upgrade = (
            "Improve response quality through conversation examples."
        )

    return ConversationQualityScore(
        overall_score=max(0, min(100, overall)),
        continuity=max(0, min(100, continuity)),
        helpfulness=max(0, min(100, helpfulness)),
        reasoning=max(0, min(100, reasoning)),
        actionability=max(0, min(100, actionability)),
        issues=issues,
        strengths=strengths,
        recommended_upgrade=recommended_upgrade,
    )


def build_quality_report(
    user_message: str = "",
    assistant_message: str = "",
    previous_context: str = "",
) -> str:
    result = evaluate_conversation(
        user_message=user_message,
        assistant_message=assistant_message,
        previous_context=previous_context,
    )

    return "\n".join(
        [
            "Nova Conversation Quality Report:",
            f"Overall Score: {result.overall_score}/100",
            f"Continuity: {result.continuity}/100",
            f"Helpfulness: {result.helpfulness}/100",
            f"Reasoning: {result.reasoning}/100",
            f"Actionability: {result.actionability}/100",
            "",
            "Strengths:",
            *[
                f"- {item}"
                for item in result.strengths
            ],
            "",
            "Issues:",
            *[
                f"- {item}"
                for item in result.issues
            ],
            "",
            f"Recommended Upgrade: {result.recommended_upgrade}",
        ]
    )