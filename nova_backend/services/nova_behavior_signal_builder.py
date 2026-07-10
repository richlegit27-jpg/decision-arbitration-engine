"""
NOVA BEHAVIOR SIGNAL BUILDER

Adapter between live conversations and
the conversation quality evaluator.

Keeps chat_service.py unaware of
behavior scoring details.
"""

from nova_backend.services.nova_conversation_quality_evaluator import (
    evaluate_conversation,
)


class NovaBehaviorSignalBuilder:

    def _detect_user_correction(
        self,
        user_text=""
    ):
        """
        Detect when the user is correcting Nova.

        This is a learning signal only.
        It must never affect normal chat flow.
        """

        try:

            text = str(
                user_text or ""
            ).lower().strip()

            if not text:
                return {
                    "user_correction": False,
                }

            correction_patterns = [
                "no, that is wrong",
                "that's wrong",
                "that is wrong",
                "you are wrong",
                "you misunderstood",
                "not what i meant",
                "i meant",
                "actually",
                "wrong thing",
                "no i meant",
            ]

            matched = any(
                pattern in text
                for pattern in correction_patterns
            )

            if not matched:
                return {
                    "user_correction": False,
                }

            return {
                "user_correction": True,
                "correction_confidence": "high",
                "correction_text": user_text,
            }

        except Exception:

            return {
                "user_correction": False,
            }


    def build(
        self,
        user_text="",
        assistant_text="",
        context="",
    ):
        """
        Create behavior evaluation signals
        from a completed conversation turn.
        """

        try:

            result = evaluate_conversation(
                user_text or "",
                assistant_text or "",
                context or "",
            )

            if hasattr(result, "as_dict"):
                payload = result.as_dict()

            elif isinstance(result, dict):
                payload = result

            else:
                payload = {
                    "overall_score": 100,
                    "continuity": 100,
                    "helpfulness": 100,
                    "reasoning": 100,
                    "actionability": 100,
                    "issues": [],
                    "strengths": [],
                }


            payload.update(
                self._detect_user_correction(
                    user_text
                )
            )

            return payload


        except Exception as exc:

            return {
                "overall_score": 0,
                "continuity": 0,
                "helpfulness": 0,
                "reasoning": 0,
                "actionability": 0,
                "issues": [
                    f"behavior evaluation failed: {exc}"
                ],
                "strengths": [],
                "user_correction": False,
            }


behavior_signal_builder = (
    NovaBehaviorSignalBuilder()
)