from nova_backend.tools.registry import registry

from nova_backend.tools.memory_tool import MemoryWriteTool
from nova_backend.tools.apply_pending_fix_tool import ApplyPendingFixTool
from nova_backend.tools.memory_read_tool import MemoryReadTool
from nova_backend.tools.memory_delete_tool import MemoryDeleteTool

from nova_backend.tools.project_workspace_tool import ProjectWorkspaceTool
from nova_backend.tools.project_tree_tool import ProjectTreeTool

from nova_backend.tools.file_read_tool import FileReadTool
from nova_backend.tools.file_list_tool import FileListTool
from nova_backend.tools.file_write_tool import FileWriteTool
from nova_backend.tools.file_delete_tool import FileDeleteTool
from nova_backend.tools.file_move_tool import FileMoveTool
from nova_backend.tools.file_exists_tool import FileExistsTool
from nova_backend.tools.file_info_tool import FileInfoTool
from nova_backend.tools.file_copy_tool import FileCopyTool
from nova_backend.tools.file_append_tool import FileAppendTool

from nova_backend.tools.directory_create_tool import DirectoryCreateTool
from nova_backend.tools.directory_delete_tool import DirectoryDeleteTool
from nova_backend.tools.directory_list_tool import DirectoryListTool

from nova_backend.tools.code_search_tool import CodeSearchTool
from nova_backend.tools.code_replace_tool import CodeReplaceTool
from nova_backend.tools.text_search_tool import TextSearchTool

from nova_backend.tools.git_status_tool import GitStatusTool
from nova_backend.tools.git_diff_tool import GitDiffTool
from nova_backend.tools.git_log_tool import GitLogTool
from nova_backend.tools.git_show_tool import GitShowTool
from nova_backend.tools.git_commit_tool import GitCommitTool

from nova_backend.tools.shell_command_tool import ShellCommandTool
from nova_backend.tools.terminal_execute_tool import TerminalExecuteTool

from nova_backend.tools.process_list_tool import ProcessListTool
from nova_backend.tools.process_start_tool import ProcessStartTool
from nova_backend.tools.process_stop_tool import ProcessStopTool

from nova_backend.tools.port_check_tool import PortCheckTool
from nova_backend.tools.python_compile_tool import PythonCompileTool
from nova_backend.tools.python_run_tool import PythonRunTool
from nova_backend.tools.json_validate_tool import JsonValidateTool
from nova_backend.tools.environment_get_tool import EnvironmentGetTool
from nova_backend.tools.working_directory_tool import WorkingDirectoryTool
from nova_backend.tools.disk_usage_tool import DiskUsageTool


def load_tools(chat_service=None):

    tools = [

        # MEMORY
        MemoryWriteTool(),
        MemoryReadTool(),
        MemoryDeleteTool(),

        # LEGACY CHAT WORKFLOW ADAPTERS
        ApplyPendingFixTool(
            chat_service=chat_service,
        ),

        # PROJECT / WORKSPACE
        ProjectWorkspaceTool(),
        ProjectTreeTool(),

        # FILE SYSTEM
        FileReadTool(),
        FileListTool(),
        FileWriteTool(),
        FileDeleteTool(),
        FileMoveTool(),
        FileExistsTool(),
        FileInfoTool(),
        FileCopyTool(),
        FileAppendTool(),

        # DIRECTORIES
        DirectoryCreateTool(),
        DirectoryDeleteTool(),
        DirectoryListTool(),

        # CODE / SEARCH
        CodeSearchTool(),
        CodeReplaceTool(),
        TextSearchTool(),

        # GIT
        GitStatusTool(),
        GitDiffTool(),
        GitLogTool(),
        GitShowTool(),
        GitCommitTool(),

        # TERMINAL / SHELL
        ShellCommandTool(),
        TerminalExecuteTool(),

        # PROCESS
        ProcessListTool(),
        ProcessStartTool(),
        ProcessStopTool(),

        # DEVELOPMENT
        PythonCompileTool(),
        PythonRunTool(),
        JsonValidateTool(),

        # SYSTEM
        PortCheckTool(),
        EnvironmentGetTool(),
        WorkingDirectoryTool(),
        DiskUsageTool(),
    ]

    for tool in tools:
        registry.register(tool)

    return registry
