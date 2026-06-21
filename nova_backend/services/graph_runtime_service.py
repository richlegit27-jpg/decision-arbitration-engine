import copy


class GraphRuntimeService:
    def __init__(self):
        self.graph_snapshots = {
            "stable_graphs": {},
            "failure_states": {},
        }

        self.graph_memory = {
            "graph_scores": {},
            "graph_usage": {},
            "context_map": {},
        }

        self.graph_stability = {
            "mutation_pressure": {},
            "stability_scores": {},
        }

    def _safe_dict(self, value):
        return value if isinstance(value, dict) else {}

    def _clone(self, value):
        try:
            return copy.deepcopy(value)
        except Exception:
            return value

    def detect_graph_failure(self, execution_summary):
        execution_summary = self._safe_dict(execution_summary)

        failed = execution_summary.get("failed_count", 0)
        complete = execution_summary.get("complete", False)

        if failed > 2:
            return "hard_failure"

        if failed > 0 and not complete:
            return "soft_failure"

        return None

    def get_context_signature(self, execution_state):
        execution_state = self._safe_dict(execution_state)

        steps = execution_state.get("steps") or []
        status = execution_state.get("status")

        signature = {
            "step_count": len(steps),
            "status": status,
            "failure_count": sum(
                1
                for step in steps
                if isinstance(step, dict)
                and step.get("status") == "failed"
            ),
        }

        return str(signature)

    def select_best_graph(self, execution_state):
        execution_state = self._safe_dict(execution_state)

        memory = self.graph_memory
        graph = execution_state.get("graph") or {}

        context = self.get_context_signature(execution_state)

        if context in memory["context_map"]:
            best_graph = memory["context_map"][context]
            graph["active_graph_variant"] = best_graph
            execution_state["graph"] = graph
            return execution_state

        best_graph = None
        best_score = -999

        for graph_id, score in memory["graph_scores"].items():
            usage = memory["graph_usage"].get(graph_id, 1)
            adjusted_score = score / (1 + (1 / usage))

            if adjusted_score > best_score:
                best_score = adjusted_score
                best_graph = graph_id

        if best_graph:
            graph["active_graph_variant"] = best_graph
            memory["context_map"][context] = best_graph

        execution_state["graph"] = graph

        return execution_state

    def apply_runtime_to_graph(
        self,
        execution_state,
        final_action,
        strategy_memory=None,
        meta_policy=None,
    ):
        execution_state = self._safe_dict(execution_state)
        strategy_memory = self._safe_dict(strategy_memory)
        meta_policy = self._safe_dict(meta_policy)

        graph = execution_state.get("graph") or {}
        nodes = graph.get("nodes") or {}
        current_id = graph.get("current_node")

        if not current_id or current_id not in nodes:
            execution_state["graph"] = graph
            return execution_state

        node = nodes[current_id]

        if final_action == "retry":
            node["runtime_hint"] = "force_retry_path"

        elif final_action == "pause":
            node["runtime_hint"] = "pause_execution"

        elif final_action == "continue":
            node["runtime_hint"] = "prefer_forward_path"

        node["strategy_bias"] = {
            "retry": strategy_memory.get("retry_strategy_score", 0.5),
            "continue": strategy_memory.get("continue_strategy_score", 0.5),
            "pause": strategy_memory.get("pause_strategy_score", 0.5),
        }

        node["adaptation_level"] = meta_policy.get(
            "adaptation_speed",
            1.0,
        )

        execution_state["graph"] = graph

        return execution_state

    def prune_graph(self, execution_state):
        execution_state = self._safe_dict(execution_state)

        graph = execution_state.get("graph") or {}
        nodes = graph.get("nodes") or {}

        if not nodes:
            execution_state["graph"] = graph
            return execution_state

        pruned_nodes = []

        for node_id, node in nodes.items():
            if not isinstance(node, dict):
                continue

            success = node.get("success_count", 0)
            failure = node.get("failure_count", 0)
            confidence = node.get("avg_confidence", 0.5)

            total = success + failure

            low_activity = total < 2
            low_confidence = confidence < 0.35
            high_failure = (
                failure > success * 2
                if success > 0
                else failure > 2
            )

            if low_activity or low_confidence or high_failure:
                node["pruned"] = True
                node["status"] = "inactive"
                pruned_nodes.append(node_id)

        graph["pruned_nodes"] = pruned_nodes
        execution_state["graph"] = graph

        return execution_state

    def compress_graph(self, execution_state):
        execution_state = self._safe_dict(execution_state)

        graph = execution_state.get("graph") or {}
        nodes = graph.get("nodes") or {}

        if not nodes:
            execution_state["graph"] = graph
            return execution_state

        merged = {}
        visited = set()

        def similarity(node_a, node_b):
            action_match = node_a.get("action") == node_b.get("action")

            bias_a = node_a.get("strategy_bias") or {}
            bias_b = node_b.get("strategy_bias") or {}

            bias_diff = 0.0

            for key in ["retry", "continue", "pause"]:
                bias_diff += abs(
                    bias_a.get(key, 0)
                    - bias_b.get(key, 0)
                )

            confidence_diff = abs(
                node_a.get("avg_confidence", 0.5)
                - node_b.get("avg_confidence", 0.5)
            )

            score = bias_diff + confidence_diff

            return action_match and score < 0.25

        node_items = list(nodes.items())

        for index, (node_id, node) in enumerate(node_items):
            if node_id in visited:
                continue

            if not isinstance(node, dict):
                continue

            cluster = [node_id]

            for other_id, other_node in node_items[index + 1:]:
                if other_id in visited:
                    continue

                if not isinstance(other_node, dict):
                    continue

                if similarity(node, other_node):
                    cluster.append(other_id)
                    visited.add(other_id)

            if len(cluster) == 1:
                merged[node_id] = node
                visited.add(node_id)
                continue

            super_id = f"super_{node_id}"

            success_total = sum(
                nodes[item].get("success_count", 0)
                for item in cluster
                if isinstance(nodes.get(item), dict)
            )

            failure_total = sum(
                nodes[item].get("failure_count", 0)
                for item in cluster
                if isinstance(nodes.get(item), dict)
            )

            merged[super_id] = {
                "id": super_id,
                "type": "supernode",
                "merged_nodes": cluster,
                "success_count": success_total,
                "failure_count": failure_total,
                "avg_confidence": success_total / (
                    success_total
                    + failure_total
                    + 1e-6
                ),
                "compressed": True,
            }

            visited.update(cluster)

        graph["nodes"] = merged
        graph["compression_pass"] = True
        execution_state["graph"] = graph

        return execution_state

    def update_graph_memory(
        self,
        execution_state,
        execution_summary,
    ):
        execution_state = self._safe_dict(execution_state)
        execution_summary = self._safe_dict(execution_summary)

        graph = execution_state.get("graph") or {}
        graph_id = graph.get("id", "default_graph")

        memory = self.graph_memory

        if graph_id not in memory["graph_scores"]:
            memory["graph_scores"][graph_id] = 0.5
            memory["graph_usage"][graph_id] = 0

        memory["graph_usage"][graph_id] += 1

        score_delta = 0.0

        if execution_summary.get("complete"):
            score_delta += 0.1

        if execution_summary.get("failed_count", 0) > 0:
            score_delta -= 0.15

        if execution_summary.get("steps_count", 0) > 5:
            score_delta += 0.02

        learning_rate = 0.1

        memory["graph_scores"][graph_id] = (
            (1 - learning_rate)
            * memory["graph_scores"][graph_id]
            + learning_rate
            * (0.5 + score_delta)
        )

        execution_state["graph_memory"] = memory

        return execution_state

    def snapshot_graph(self, execution_state):
        execution_state = self._safe_dict(execution_state)

        graph = execution_state.get("graph") or {}
        graph_id = graph.get("id", "default_graph")

        snapshots = self.graph_snapshots["stable_graphs"]

        if graph_id not in snapshots:
            snapshots[graph_id] = self._clone(graph)

        if execution_state.get("status") == "completed":
            snapshots[graph_id] = self._clone(graph)

        return execution_state

    def repair_graph(self, execution_state, failure_type):
        execution_state = self._safe_dict(execution_state)

        graph = execution_state.get("graph") or {}
        graph_id = graph.get("id", "default_graph")

        snapshots = self.graph_snapshots["stable_graphs"]

        if failure_type == "hard_failure" and graph_id in snapshots:
            execution_state["graph"] = self._clone(snapshots[graph_id])
            execution_state["repair_action"] = "rollback_to_last_stable"
            return execution_state

        nodes = graph.get("nodes") or {}

        for node in nodes.values():
            if not isinstance(node, dict):
                continue

            if node.get("failure_count", 0) > node.get("success_count", 0):
                node["strategy_bias"] = {
                    "retry": 0.7,
                    "continue": 0.2,
                    "pause": 0.1,
                }

                node["runtime_hint"] = "stabilize_path"

        execution_state["graph"] = graph
        execution_state["repair_action"] = "localized_stabilization"

        return execution_state

    def update_node_feedback(
        self,
        execution_state,
        node=None,
        result=None,
    ):
        execution_state = self._safe_dict(execution_state)

        graph = execution_state.get("graph") or {}
        nodes = graph.get("nodes") or {}
        current_id = graph.get("current_node")

        if not current_id or current_id not in nodes:
            execution_state["graph"] = graph
            return execution_state

        current_node = nodes[current_id]

        if not isinstance(current_node, dict):
            execution_state["graph"] = graph
            return execution_state

        if "success_count" not in current_node:
            current_node["success_count"] = 0

        if "failure_count" not in current_node:
            current_node["failure_count"] = 0

        if "avg_confidence" not in current_node:
            current_node["avg_confidence"] = 0.5

        if current_node.get("status") == "completed":
            current_node["success_count"] += 1

        elif current_node.get("status") == "failed":
            current_node["failure_count"] += 1

        learning_rate = 0.1

        success_rate = current_node["success_count"] / (
            current_node["success_count"]
            + current_node["failure_count"]
            + 1e-6
        )

        current_node["avg_confidence"] = (
            (1 - learning_rate)
            * current_node["avg_confidence"]
            + learning_rate
            * success_rate
        )

        execution_state["graph"] = graph

        return execution_state

    def update_mutation_pressure(self, graph_id, execution_state):
        execution_state = self._safe_dict(execution_state)

        stability = self.graph_stability

        if graph_id not in stability["mutation_pressure"]:
            stability["mutation_pressure"][graph_id] = 0.5

        graph = execution_state.get("graph") or {}
        nodes = graph.get("nodes") or {}

        changes = sum(
            1
            for node in nodes.values()
            if isinstance(node, dict)
            and (
                node.get("runtime_hint")
                or node.get("pruned")
            )
        )

        pressure = changes / (len(nodes) + 1e-6)

        learning_rate = 0.1

        stability["mutation_pressure"][graph_id] = (
            (1 - learning_rate)
            * stability["mutation_pressure"][graph_id]
            + learning_rate
            * pressure
        )

        return stability["mutation_pressure"][graph_id]

    def update_stability_score(self, graph_id):
        stability = self.graph_stability

        mutation_pressure = stability["mutation_pressure"].get(
            graph_id,
            0.5,
        )

        score = 1.0 - mutation_pressure

        if graph_id not in stability["stability_scores"]:
            stability["stability_scores"][graph_id] = 0.5

        learning_rate = 0.1

        stability["stability_scores"][graph_id] = (
            (1 - learning_rate)
            * stability["stability_scores"][graph_id]
            + learning_rate
            * score
        )

        return stability["stability_scores"][graph_id]

    def run_graph_pipeline(
        self,
        execution_state,
        final_action,
        execution_summary,
        failure_type=None,
        control=None,
        strategy_memory=None,
        meta_policy=None,
    ):
        execution_state = self._safe_dict(execution_state)
        execution_summary = self._safe_dict(execution_summary)
        control = self._safe_dict(control)

        allow = control.get("allow") or {}
        mode = control.get("mode", "explore")

        execution_state = self.select_best_graph(execution_state)

        execution_state = self.apply_runtime_to_graph(
            execution_state=execution_state,
            final_action=final_action,
            strategy_memory=strategy_memory,
            meta_policy=meta_policy,
        )

        if allow.get("pruning", True):
            execution_state = self.prune_graph(execution_state)

        if allow.get("compression", True):
            execution_state = self.compress_graph(execution_state)

        if allow.get("evolution", True):
            execution_state = self.update_graph_memory(
                execution_state=execution_state,
                execution_summary=execution_summary,
            )

        graph = execution_state.get("graph") or {}
        graph_id = graph.get("id", "default_graph")

        self.update_mutation_pressure(
            graph_id=graph_id,
            execution_state=execution_state,
        )

        self.update_stability_score(graph_id)

        self.snapshot_graph(execution_state)

        if failure_type and mode == "repair_only":
            execution_state = self.repair_graph(
                execution_state=execution_state,
                failure_type=failure_type,
            )

        return execution_state

