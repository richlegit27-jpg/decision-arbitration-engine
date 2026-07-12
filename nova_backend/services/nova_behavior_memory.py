"""
NOVA BEHAVIOR MEMORY

Stores repeated conversation behavior signals
and converts them into improvement priorities.

Persistent version.
"""

import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone


BEHAVIOR_MEMORY_PATH = (
    Path(__file__)
    .resolve()
    .parents[2]
    / "data"
    / "nova_behavior_memory.json"
)


class NovaBehaviorMemory:

    def __init__(self):

        self.events = []

        self._load()


    def _load(self):

        try:

            if BEHAVIOR_MEMORY_PATH.exists():

                with open(
                    BEHAVIOR_MEMORY_PATH,
                    "r",
                    encoding="utf-8"
                ) as file:

                    data = json.load(file)


                if isinstance(data, list):

                    self.events = data


                elif isinstance(data, dict):

                    events = data.get(
                        "events",
                        []
                    )

                    if isinstance(events, list):

                        self.events = events


        except Exception as exc:

            print(
                "[NOVA_BEHAVIOR_MEMORY_LOAD_FAILED]",
                exc
            )


    def _save(self):

        try:

            BEHAVIOR_MEMORY_PATH.parent.mkdir(
                parents=True,
                exist_ok=True
            )

            with open(
                BEHAVIOR_MEMORY_PATH,
                "w",
                encoding="utf-8"
            ) as file:

                json.dump(
                    self.events,
                    file,
                    indent=2,
                    ensure_ascii=False
                )


        except Exception as exc:

            print(
                "[NOVA_BEHAVIOR_MEMORY_SAVE_FAILED]",
                exc
            )


    def record_behavior(self, behavior_upgrade):

        if hasattr(behavior_upgrade, "as_dict"):

            data = behavior_upgrade.as_dict()

        else:

            data = dict(
                behavior_upgrade or {}
            )


        event = {

            "timestamp":
                datetime.now(
                    timezone.utc
                ).isoformat(),

            "behavior_problem":
                data.get(
                    "behavior_problem",
                    "unknown"
                ),

            "severity":
                data.get(
                    "severity",
                    "unknown"
                ),

            "upgrade":
                data.get(
                    "upgrade",
                    ""
                ),

            "action":
                data.get(
                    "action",
                    ""
                ),

            "reason":
                data.get(
                    "reason",
                    ""
                ),
        }


        self.events.append(event)

        self._save()

        return event



    def get_behavior_counts(self):

        counts = defaultdict(int)

        for event in self.events:

            counts[
                event["behavior_problem"]
            ] += 1


        return dict(counts)



    def rank_behavior_problems(self):

        problem_scores = defaultdict(
            lambda: {
                "occurrences": 0,
                "severity_score": 0
            }
        )


        severity_weights = {
            "critical": 5,
            "high": 3,
            "medium": 2,
            "low": 1,
        }


        ignored_problems = {
            "no_major_behavior_issue",
            "none",
            "unknown",
            "",
        }


        for event in self.events:

            problem = event.get(
                "behavior_problem",
                "unknown"
            )


            if problem in ignored_problems:
                continue


            severity = event.get(
                "severity",
                "low"
            )


            problem_scores[problem][
                "occurrences"
            ] += 1


            problem_scores[problem][
                "severity_score"
            ] += severity_weights.get(
                severity,
                0
            )


        ranked = []


        for problem, data in problem_scores.items():

            total_score = (
                data["occurrences"]
                +
                data["severity_score"]
            )


            if total_score >= 10:
                priority = "critical"

            elif total_score >= 6:
                priority = "high"

            elif total_score >= 3:
                priority = "medium"

            else:
                priority = "low"


            ranked.append(
                {
                    "problem": problem,
                    "occurrences": data["occurrences"],
                    "severity_score": data["severity_score"],
                    "score": total_score,
                    "priority": priority,
                }
            )


        ranked.sort(
            key=lambda item: item["score"],
            reverse=True
        )


        return ranked


    def create_improvement_priority(self):

        ranked = self.rank_behavior_problems()


        if not ranked:

            return {
                "focus":
                    "collect_behavior_data",

                "priority":
                    "low",

                "reason":
                    "No behavior history exists yet."
            }


        top = ranked[0]


        return {

            "focus":
                top["problem"],

            "priority":
                top["priority"],

            "reason":
                (
                    f'{top["problem"]} detected '
                    f'{top["occurrences"]} times.'
                )
        }



    def export_report(self):

        return {

            "total_events":
                len(self.events),

            "behavior_counts":
                self.get_behavior_counts(),

            "ranked_problems":
                self.rank_behavior_problems(),

            "recommended_focus":
                self.create_improvement_priority(),
        }



behavior_memory = NovaBehaviorMemory()