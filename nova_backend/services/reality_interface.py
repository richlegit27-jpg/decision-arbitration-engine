from datetime import datetime
import platform
import psutil
import os


class RealityInterface:

    def observe_environment(self):

        return {
            "timestamp": (
                datetime.utcnow()
                .isoformat()
            ),
            "platform": (
                platform.platform()
            ),
            "python_version": (
                platform.python_version()
            ),
            "cpu_percent": (
                psutil.cpu_percent()
            ),
            "memory_percent": (
                psutil.virtual_memory()
                .percent
            ),
            "disk_percent": (
                psutil.disk_usage("/")
                .percent
            ),
            "cwd": os.getcwd(),
        }

    def evaluate_environment(
        self,
        environment_state=None,
    ):

        environment_state = (
            environment_state
            if isinstance(
                environment_state,
                dict,
            )
            else {}
        )

        alerts = []

        cpu = float(
            environment_state.get(
                "cpu_percent",
                0,
            )
        )

        memory = float(
            environment_state.get(
                "memory_percent",
                0,
            )
        )

        disk = float(
            environment_state.get(
                "disk_percent",
                0,
            )
        )

        if cpu > 90:

            alerts.append({
                "type": (
                    "high_cpu_usage"
                ),
                "severity": "high",
            })

        if memory > 90:

            alerts.append({
                "type": (
                    "high_memory_usage"
                ),
                "severity": "high",
            })

        if disk > 95:

            alerts.append({
                "type": (
                    "low_disk_space"
                ),
                "severity": "critical",
            })

        return {
            "ok": True,
            "alerts": alerts,
        }

