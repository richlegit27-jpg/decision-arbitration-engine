from nova_backend.tools.registry import registry

from nova_backend.tools.memory_tool import (
    MemoryWriteTool,
)
from nova_backend.tools.memory_read_tool import (
    MemoryReadTool,
)
from nova_backend.tools.memory_delete_tool import (
    MemoryDeleteTool,
)

from nova_backend.tools.project_workspace_tool import (
    ProjectWorkspaceTool,
)

from nova_backend.tools.file_read_tool import (
    FileReadTool,
)
from nova_backend.tools.file_list_tool import (
    FileListTool,
)
from nova_backend.tools.file_write_tool import (
    FileWriteTool,
)
from nova_backend.tools.file_delete_tool import (
    FileDeleteTool,
)
from nova_backend.tools.file_move_tool import (
    FileMoveTool,
)

from nova_backend.tools.directory_create_tool import (
    DirectoryCreateTool,
)

from nova_backend.tools.code_search_tool import (
    CodeSearchTool,
)
from nova_backend.tools.code_replace_tool import (
    CodeReplaceTool,
)

from nova_backend.tools.git_status_tool import (
    GitStatusTool,
)
from nova_backend.tools.git_diff_tool import (
    GitDiffTool,
)
from nova_backend.tools.git_log_tool import (
    GitLogTool,
)
from nova_backend.tools.git_show_tool import (
    GitShowTool,
)
from nova_backend.tools.git_commit_tool import (
    GitCommitTool,
)

from nova_backend.tools.shell_command_tool import (
    ShellCommandTool,
)
from nova_backend.tools.terminal_execute_tool import (
    TerminalExecuteTool,
)

from nova_backend.tools.process_list_tool import (
    ProcessListTool,
)
from nova_backend.tools.process_start_tool import (
    ProcessStartTool,
)


def load_tools():

    tools = [

        # MEMORY
        MemoryWriteTool(),
        MemoryReadTool(),
        MemoryDeleteTool(),

        # WORKSPACE
        ProjectWorkspaceTool(),

        # FILE SYSTEM
        FileReadTool(),
        FileListTool(),
        FileWriteTool(),
        FileDeleteTool(),
        FileMoveTool(),
        DirectoryCreateTool(),

        # CODE
        CodeSearchTool(),
        CodeReplaceTool(),

        # GIT
        GitStatusTool(),
        GitDiffTool(),
        GitLogTool(),
        GitShowTool(),
        GitCommitTool(),

        # TERMINAL
        ShellCommandTool(),
        TerminalExecuteTool(),

        # PROCESSES
        ProcessListTool(),
        ProcessStartTool(),
    ]

    for tool in tools:
        registry.register(tool)
