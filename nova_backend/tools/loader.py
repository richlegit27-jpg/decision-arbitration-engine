from nova_backend.tools.registry import registry

from nova_backend.tools.project_workspace_tool import ProjectWorkspaceTool
from nova_backend.tools.memory_tool import MemoryWriteTool
from nova_backend.tools.memory_read_tool import MemoryReadTool
from nova_backend.tools.memory_delete_tool import MemoryDeleteTool

def load_tools():

    registry.register(
        MemoryWriteTool()
    )

    registry.register(
        MemoryReadTool()
    )

    registry.register(
        MemoryDeleteTool()
    )

    registry.register(
        ProjectWorkspaceTool()
    )