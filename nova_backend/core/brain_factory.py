from nova_backend.core.nova_orchestrator import (
    NovaOrchestrator,
)


class BrainFactory:


    @staticmethod
    def create():

        orchestrator = NovaOrchestrator()

        return orchestrator