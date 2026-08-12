from typing import Dict, Any, List


class ToolRegistryService:

    def __init__(self):
        self.tools = {
            "file_analyzer": {
                "name": "File Analyzer",
                "description": "Analyze files and project structure.",
                "category": "analysis",
            },
            "code_reviewer": {
                "name": "Code Reviewer",
                "description": "Review code changes and identify issues.",
                "category": "development",
            },
            "test_runner": {
                "name": "Test Runner",
                "description": "Run focused tests and validation checks.",
                "category": "verification",
            },
            "documentation_writer": {
                "name": "Documentation Writer",
                "description": "Create README files and documentation.",
                "category": "writing",
            },
            "deployment_checker": {
                "name": "Deployment Checker",
                "description": "Check deployment readiness.",
                "category": "deployment",
            },
        }

    def list_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": tool_id,
                **tool,
            }
            for tool_id, tool in self.tools.items()
        ]

    def get_tool(self, tool_id: str):
        return self.tools.get(tool_id)


tool_registry_service = ToolRegistryService()