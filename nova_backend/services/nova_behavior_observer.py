"""
NOVA BEHAVIOR OBSERVER

Safe observer layer.

Receives completed conversation signals
and sends them through the behavior learning loop.

The observer never controls responses.
It only records improvement signals.
"""

from nova_backend.services.nova_behavior_learning_loop import (
    process_conversation_behavior,
)


class NovaBehaviorObserver:


    def __init__(self):
        self.enabled = True



    def observe(
        self,
        evaluation
    ):
        """
        Analyze completed conversation behavior.

        Failure in learning must never break chat.
        """

        if not self.enabled:
            return {
                "observed": False,
                "reason": "observer_disabled",
            }


        try:

            result = (
                process_conversation_behavior(
                    evaluation
                )
            )

            return {
                "observed": True,
                "result": result,
            }


        except Exception as exc:

            return {
                "observed": False,
                "error": str(exc),
            }



behavior_observer = (
    NovaBehaviorObserver()
)