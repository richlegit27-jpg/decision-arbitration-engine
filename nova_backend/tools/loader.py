from nova_backend.tools.registry import registry
from nova_backend.tools.project_workspace_tool import ProjectWorkspaceTool


def load_tools():
    registry.register(
        ProjectWorkspaceTool()
    )