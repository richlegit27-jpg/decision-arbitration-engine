from nova_backend.services.safe_unified_runtime import (
    SafeUnifiedRuntime,
)


class RuntimeBootstrap:
    @staticmethod
    def build(chat_service=None):
        return SafeUnifiedRuntime(
            chat_service=chat_service,
        )