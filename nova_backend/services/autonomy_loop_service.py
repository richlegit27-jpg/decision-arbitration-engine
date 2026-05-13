import time


class AutonomyLoopService:

    def __init__(
        self,
        agent_kernel=None,
        world_state=None,
    ):

        self.agent_kernel = (
            agent_kernel
        )

        self.world_state = (
            world_state
        )

        self.running = False

    def start(
        self,
        execution_state=None,
        max_cycles=10,
        cycle_delay=1,
    ):

        self.running = True

        cycles = []

        current_state = (
            execution_state
            if isinstance(
                execution_state,
                dict,
            )
            else {}
        )

        for cycle in range(
            1,
            max_cycles + 1,
        ):

            if not self.running:

                break

            kernel_result = (
                self.agent_kernel.run(
                    execution_state=(
                        current_state
                    )
                )
            )

            cycles.append({
                "cycle": cycle,
                "result": kernel_result,
            })

            if kernel_result.get("ok"):

                mission_result = (
                    kernel_result.get(
                        "mission_result",
                        {}
                    )
                )

                execution = (
                    mission_result.get(
                        "execution_state",
                        {}
                    )
                )

                steps = (
                    execution.get(
                        "steps",
                        []
                    )
                )

                unfinished = [
                    s
                    for s in steps
                    if str(
                        s.get(
                            "status"
                        )
                        or ""
                    ).lower()
                    != "completed"
                ]

                if not unfinished:

                    return {
                        "ok": True,
                        "cycles": cycles,
                        "reason": (
                            "mission_complete"
                        ),
                    }

            current_state = (
                kernel_result
                .get(
                    "mission_result",
                    {}
                )
                .get(
                    "execution_state",
                    {}
                )
            )

            time.sleep(
                cycle_delay
            )

        return {
            "ok": False,
            "cycles": cycles,
            "reason": (
                "max_cycles_reached"
            ),
        }

    def stop(self):

        self.running = False

        return {
            "ok": True,
            "status": "stopped",
        }