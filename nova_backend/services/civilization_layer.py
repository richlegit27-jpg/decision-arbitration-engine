class CivilizationLayer:

    def __init__(self):

        self.agents = {}

    def register_agent(
        self,
        agent_id="",
        role="general",
        capabilities=None,
    ):

        capabilities = (
            capabilities
            if isinstance(
                capabilities,
                list,
            )
            else []
        )

        self.agents[agent_id] = {
            "id": agent_id,
            "role": role,
            "capabilities": (
                capabilities
            ),
            "status": "active",
            "task_history": [],
        }

    def assign_task(
        self,
        agent_id="",
        task=None,
    ):

        if (
            agent_id
            not in self.agents
        ):

            return {
                "ok": False,
                "error": (
                    "Agent not found."
                ),
            }

        task = (
            task
            if isinstance(
                task,
                dict,
            )
            else {}
        )

        self.agents[
            agent_id
        ][
            "task_history"
        ].append(task)

        return {
            "ok": True,
            "agent": (
                self.agents[
                    agent_id
                ]
            ),
        }

    def collaboration_map(self):

        collaborations = []

        for agent_id, data in (
            self.agents.items()
        ):

            collaborations.append({
                "agent_id": (
                    agent_id
                ),
                "role": (
                    data.get(
                        "role"
                    )
                ),
                "capabilities": (
                    data.get(
                        "capabilities",
                        [],
                    )
                ),
                "tasks_completed": len(
                    data.get(
                        "task_history",
                        [],
                    )
                ),
            })

        return collaborations

    def summarize(self):

        return {
            "agents": len(
                self.agents
            ),
            "active_agents": len([
                a
                for a in self.agents.values()
                if a.get("status")
                == "active"
            ]),
        }