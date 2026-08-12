from nova_backend.tools.registry import registry
from nova_backend.tools.project_workspace_tool import ProjectWorkspaceTool
from nova_backend.tools.memory_tool import MemoryWriteTool
registry.register(
    MemoryWriteTool()
)

def load_tools():
    registry.register(
        ProjectWorkspaceTool()
    )