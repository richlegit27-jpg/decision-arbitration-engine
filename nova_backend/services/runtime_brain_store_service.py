import json
import os
import time
from copy import deepcopy


class RuntimeBrainStoreService:

    """
    Persistent runtime brain memory.

    Persists:
    - fusion state
    - engine performance
    - recurring failures
    - successful runtime strategies
    - policy pressure
    - runtime lessons
    """

    def __init__(self, store_path=None):

        base_dir = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "..",
            )
        )

        data_dir = os.path.join(
            base_dir,
            "data",
        )

        self.store_path = (
            store_path
            or os.path.join(
                data_dir,
                "runtime_brain_store.json",
            )
        )

        self.state = self._load()

    # =========================================
    # SAFETY
    # =========================================

    def _safe_dict(self, value):

        return (
            value
            if isinstance(value, dict)
            else {}
        )

    def _safe_list(self, value):

        return (
            value
            if isinstance(value, list)
            else []
        )

    def _now(self):

        return int(time.time())

    # =========================================
    # DEFAULT STATE
    # =========================================

    def _default_state(self):

        return {
            "version": 1,
            "updated_at": self._now(),
            "cycle_count": 0,
            "last_fusion": {},
            "engine_scores": {},
            "recurring_failures": {},
            "successful_strategies": {},
            "policy_pressure": {},
            "runtime_lessons": [],
        }

    # =========================================
    # LOAD
    # =========================================

    def _load(self):

        try:

            if not os.path.exists(
                self.store_path
            ):

                state = self._default_state()

                self._save_state(state)

                return state

            with open(
                self.store_path,
                "r",
                encoding="utf-8",
            ) as file:

                loaded = json.load(file)

            state = self._default_state()

            if isinstance(loaded, dict):

                state.update(loaded)

            return state

        except Exception:

            return self._default_state()

    # =========================================
    # SAVE
    # =========================================

    def _save_state(self, state):

        os.makedirs(
            os.path.dirname(
                self.store_path
            ),
            exist_ok=True,
        )

        temp_path = (
            f"{self.store_path}.tmp"
        )

        with open(
            temp_path,
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                state,
                file,
                indent=2,
                ensure_ascii=False,
            )

        os.replace(
            temp_path,
            self.store_path,
        )

    def save(self):

        self.state["updated_at"] = (
            self._now()
        )

        self._save_state(
            self.state
        )

        return deepcopy(
            self.state
        )

    # =========================================
    # SNAPSHOT
    # =========================================

    def snapshot(self):

        return deepcopy(
            self.state
        )

    # =========================================
    # FUSION MEMORY
    # =========================================

    def remember_fusion(
        self,
        fusion,
    ):

        fusion = self._safe_dict(
            fusion
        )

        if not fusion:

            return self.snapshot()

        self.state[
            "last_fusion"
        ] = deepcopy(fusion)

        self.state[
            "cycle_count"
        ] = (
            int(
                self.state.get(
                    "cycle_count"
                )
                or 0
            )
            + 1
        )

        return self.save()

    # =========================================
    # ENGINE SCORES
    # =========================================

    def remember_engine_scores(
        self,
        scores,
    ):

        scores = self._safe_dict(
            scores
        )

        if not scores:

            return self.snapshot()

        engine_scores = (
            self._safe_dict(
                self.state.get(
                    "engine_scores"
                )
            )
        )

        for (
            engine_name,
            score,
        ) in scores.items():

            current = (
                self._safe_dict(
                    engine_scores.get(
                        engine_name
                    )
                )
            )

            current["last_score"] = (
                score
            )

            current["seen"] = (
                int(
                    current.get(
                        "seen"
                    )
                    or 0
                )
                + 1
            )

            current[
                "updated_at"
            ] = self._now()

            engine_scores[
                engine_name
            ] = current

        self.state[
            "engine_scores"
        ] = engine_scores

        return self.save()

    # =========================================
    # FAILURES
    # =========================================

    def remember_failure(
        self,
        failure_type,
        details=None,
    ):

        failure_type = str(
            failure_type or ""
        ).strip()

        if not failure_type:

            return self.snapshot()

        failures = (
            self._safe_dict(
                self.state.get(
                    "recurring_failures"
                )
            )
        )

        current = (
            self._safe_dict(
                failures.get(
                    failure_type
                )
            )
        )

        current["count"] = (
            int(
                current.get(
                    "count"
                )
                or 0
            )
            + 1
        )

        current[
            "last_seen_at"
        ] = self._now()

        if details is not None:

            current[
                "last_details"
            ] = details

        failures[
            failure_type
        ] = current

        self.state[
            "recurring_failures"
        ] = failures

        return self.save()

    # =========================================
    # STRATEGIES
    # =========================================

    def remember_successful_strategy(
        self,
        strategy_name,
        details=None,
    ):

        strategy_name = str(
            strategy_name or ""
        ).strip()

        if not strategy_name:

            return self.snapshot()

        strategies = (
            self._safe_dict(
                self.state.get(
                    "successful_strategies"
                )
            )
        )

        current = (
            self._safe_dict(
                strategies.get(
                    strategy_name
                )
            )
        )

        current["count"] = (
            int(
                current.get(
                    "count"
                )
                or 0
            )
            + 1
        )

        current[
            "last_success_at"
        ] = self._now()

        if details is not None:

            current[
                "last_details"
            ] = details

        strategies[
            strategy_name
        ] = current

        self.state[
            "successful_strategies"
        ] = strategies

        return self.save()

    # =========================================
    # POLICY PRESSURE
    # =========================================

    def remember_policy_pressure(
        self,
        pressure,
    ):

        pressure = self._safe_dict(
            pressure
        )

        if not pressure:

            return self.snapshot()

        policy_pressure = (
            self._safe_dict(
                self.state.get(
                    "policy_pressure"
                )
            )
        )

        for key, value in pressure.items():

            current = (
                self._safe_dict(
                    policy_pressure.get(
                        key
                    )
                )
            )

            current[
                "last_value"
            ] = value

            current["count"] = (
                int(
                    current.get(
                        "count"
                    )
                    or 0
                )
                + 1
            )

            current[
                "updated_at"
            ] = self._now()

            policy_pressure[
                key
            ] = current

        self.state[
            "policy_pressure"
        ] = policy_pressure

        return self.save()

    # =========================================
    # LESSONS
    # =========================================

    def remember_lesson(
        self,
        lesson,
        source="runtime",
    ):

        lesson = str(
            lesson or ""
        ).strip()

        source = str(
            source or "runtime"
        ).strip()

        if not lesson:

            return self.snapshot()

        lessons = (
            self._safe_list(
                self.state.get(
                    "runtime_lessons"
                )
            )
        )

        normalized = (
            lesson.lower()
        )

        for item in lessons:

            if not isinstance(
                item,
                dict,
            ):
                continue

            existing = str(
                item.get(
                    "lesson"
                )
                or ""
            ).lower()

            if existing == normalized:

                item["count"] = (
                    int(
                        item.get(
                            "count"
                        )
                        or 0
                    )
                    + 1
                )

                item[
                    "last_seen_at"
                ] = self._now()

                self.state[
                    "runtime_lessons"
                ] = lessons[-100:]

                return self.save()

        lessons.append(
            {
                "lesson": lesson,
                "source": source,
                "count": 1,
                "created_at": (
                    self._now()
                ),
                "last_seen_at": (
                    self._now()
                ),
            }
        )

        self.state[
            "runtime_lessons"
        ] = lessons[-100:]

        return self.save()

    # =========================================
    # ABSORB CYCLE
    # =========================================

    def absorb_cycle_result(
        self,
        result,
    ):

        result = self._safe_dict(
            result
        )

        if not result:

            return self.snapshot()

        fusion = (
            result.get("fusion")
            or result.get(
                "runtime_fusion"
            )
            or result.get(
                "decision"
            )
        )

        fusion = self._safe_dict(
            fusion
        )

        if fusion:

            self.remember_fusion(
                fusion
            )

        scores = (
            result.get(
                "engine_scores"
            )
            or result.get(
                "scores"
            )
        )

        scores = self._safe_dict(
            scores
        )

        if scores:

            self.remember_engine_scores(
                scores
            )

        failure_type = (
            result.get(
                "failure_type"
            )
            or result.get(
                "runtime_failure"
            )
            or result.get(
                "error_type"
            )
        )

        if failure_type:

            self.remember_failure(
                failure_type,
                details=(
                    result.get(
                        "details"
                    )
                    or result.get(
                        "error"
                    )
                ),
            )

        strategy = (
            result.get(
                "successful_strategy"
            )
            or result.get(
                "selected_strategy"
            )
            or result.get(
                "strategy"
            )
        )

        status = str(
            result.get("status")
            or ""
        ).lower()

        if (
            strategy
            and status in {
                "ok",
                "success",
                "stable",
                "completed",
            }
        ):

            self.remember_successful_strategy(
                strategy,
                details=result,
            )

        pressure = (
            result.get(
                "policy_pressure"
            )
            or result.get(
                "pressure"
            )
        )

        pressure = self._safe_dict(
            pressure
        )

        if pressure:

            self.remember_policy_pressure(
                pressure
            )

        lesson = (
            result.get(
                "lesson"
            )
            or result.get(
                "runtime_lesson"
            )
        )

        if lesson:

            self.remember_lesson(
                lesson
            )

        return self.save()

