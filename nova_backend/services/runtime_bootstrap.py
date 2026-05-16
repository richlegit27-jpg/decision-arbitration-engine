import json
import os

from nova_backend.services.safe_unified_runtime import (
    SafeUnifiedRuntime,
)


RUNTIME_STATE_FILE = os.path.join(
    os.path.dirname(
        os.path.dirname(
            os.path.dirname(__file__)
        )
    ),
    "data",
    "runtime_brain.json",
)


class RuntimeBootstrap:

    _runtime_instance = None

    @staticmethod
    def build(chat_service=None):

        if RuntimeBootstrap._runtime_instance:
            return RuntimeBootstrap._runtime_instance

        runtime = SafeUnifiedRuntime(
            chat_service=chat_service,
        )

        RuntimeBootstrap._restore_runtime_state(
            runtime
        )

        RuntimeBootstrap._runtime_instance = (
            runtime
        )

        return runtime

    @staticmethod
    def save(runtime):

        try:

            payload = {
                "last_compressed_runtime": getattr(
                    runtime,
                    "last_compressed_runtime",
                    {},
                ),
                "runtime_history": getattr(
                    runtime,
                    "runtime_history",
                    [],
                ),
                "cycle_count": getattr(
                    runtime,
                    "cycle_count",
                    0,
                ),
            }

            os.makedirs(
                os.path.dirname(
                    RUNTIME_STATE_FILE
                ),
                exist_ok=True,
            )

            with open(
                RUNTIME_STATE_FILE,
                "w",
                encoding="utf-8",
            ) as f:

                json.dump(
                    payload,
                    f,
                    indent=2,
                )

            return {
                "ok": True,
                "path": RUNTIME_STATE_FILE,
            }

        except Exception as e:

            return {
                "ok": False,
                "error": str(e),
            }

    @staticmethod
    def _restore_runtime_state(runtime):

        try:

            if not os.path.exists(
                RUNTIME_STATE_FILE
            ):
                return

            with open(
                RUNTIME_STATE_FILE,
                "r",
                encoding="utf-8",
            ) as f:

                payload = json.load(f)

            runtime.last_compressed_runtime = (
                payload.get(
                    "last_compressed_runtime",
                    {},
                )
            )

            runtime.runtime_history = (
                payload.get(
                    "runtime_history",
                    [],
                )
            )

            runtime.cycle_count = (
                payload.get(
                    "cycle_count",
                    0,
                )
            )

        except Exception:
            pass