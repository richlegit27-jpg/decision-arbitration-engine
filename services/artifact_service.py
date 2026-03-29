class ArtifactService:
    def __init__(self):
        self.artifacts = []

    def get_artifacts(self):
        return {"ok": True, "artifacts": self.artifacts}