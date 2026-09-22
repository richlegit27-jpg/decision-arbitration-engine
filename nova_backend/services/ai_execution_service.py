import os

from nova_backend.services import model_gateway_service


class AIExecutionService:

    def __init__(
        self,
        safe_str=None,
        chat_model=None,
    ):
        self.safe_str = safe_str

        self.chat_model = (
            chat_model
            or os.getenv("NOVA_CHAT_MODEL")
            or os.getenv("NOVA_MODEL")
            or "gpt-4.1-mini"
        )

    def _safe_str(
        self,
        value,
    ):
        if callable(self.safe_str):
            return self.safe_str(value)

        return str(value or "")

    def execute_step(
        self,
        session_id,
        step,
        context=None,
    ):
        step = (
            step
            if isinstance(step, dict)
            else {}
        )

        context = (
            context
            if isinstance(context, dict)
            else {}
        )

        title = self._safe_str(
            step.get("title")
        ).strip()

        description = self._safe_str(
            step.get("description")
            or step.get("text")
            or step.get("task")
            or step.get("instruction")
            or step.get("name")
        ).strip()

        action = self._safe_str(
            step.get("action")
        ).strip().lower()

        execution_mode = self._safe_str(
            step.get("execution_mode")
        ).strip().lower()

        dependencies = step.get(
            "dependencies",
            [],
        )

        if not isinstance(
            dependencies,
            list,
        ):
            dependencies = []

        expected_output = self._safe_str(
            step.get("expected_output")
        ).strip()

        completion_criteria = step.get(
            "completion_criteria",
            [],
        )

        if not isinstance(
            completion_criteria,
            list,
        ):
            completion_criteria = []

        project_context = self._safe_str(
            context.get("project_context")
        ).strip()

        previous_results = context.get(
            "previous_results"
        )

        system_prompt = (
            "You are Nova's project execution engine. "
            "Execute the assigned project task rather than merely "
            "describing how it could be done. "
            "Use the task title, description, action, and available "
            "context to produce concrete, useful work. "
            "Be precise and operational. "
            "Do not claim files were changed, commands were executed, "
            "or external actions occurred unless they actually occurred. "
            "Return the actual result of the task."
        )

        prompt_parts = []

        if action:
            prompt_parts.append(
                f"Execution action: {action}"
            )

        if execution_mode:
            prompt_parts.append(
                f"Execution mode: {execution_mode}"
            )

        if dependencies:
            prompt_parts.append(
                "Task dependencies:\n"
                + "\n".join(
                    f"- {self._safe_str(item).strip()}"
                    for item in dependencies
                    if self._safe_str(item).strip()
                )
            )

        if expected_output:
            prompt_parts.append(
                f"Expected output:\n{expected_output}"
            )

        if completion_criteria:
            prompt_parts.append(
                "Completion criteria:\n"
                + "\n".join(
                    f"- {self._safe_str(item).strip()}"
                    for item in completion_criteria
                    if self._safe_str(item).strip()
                )
            )

        if title:
            prompt_parts.append(
                f"Task title: {title}"
            )

        if description:
            prompt_parts.append(
                f"Task description:\n{description}"
            )

        if project_context:
            prompt_parts.append(
                f"Project context:\n{project_context}"
            )

        if previous_results:
            prompt_parts.append(
                "Previous execution results:\n"
                + self._safe_str(previous_results)
            )

        user_prompt = "\n\n".join(
            part
            for part in prompt_parts
            if part
        )

        if not user_prompt:
            raise ValueError(
                "Execution step has no usable task content."
            )

        response = self._create_response(
            session_id=session_id,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        output = self._extract_response_text(
            response
        ).strip()

        if not output:
            raise RuntimeError(
                "AI execution returned an empty result."
            )

        return {
            "ok": True,
            "output": output,
        }

    def _validate_generated_file_content(
        self,
        content,
    ):
        content = self._safe_str(
            content
        ).strip()

        if not content:
            raise RuntimeError(
                "AI file replacement generation produced empty content."
            )

        first_line = content.splitlines()[0].strip().lower()

        status_prefixes = (
            "created file:",
            "updated file:",
            "modified file:",
            "written file:",
            "saved file:",
            "successfully created",
            "successfully updated",
            "successfully modified",
            "file created:",
            "file updated:",
            "file modified:",
        )

        if first_line.startswith(status_prefixes):
            raise RuntimeError(
                "AI file replacement generation returned a "
                "status message instead of file contents: "
                + content.splitlines()[0].strip()
            )

        return content

    def generate_file_replacement(
        self,
        session_id,
        step,
        context=None,
    ):
        step = (
            step
            if isinstance(step, dict)
            else {}
        )

        context = (
            context
            if isinstance(context, dict)
            else {}
        )

        target_file = self._safe_str(
            step.get("target_file")
        ).strip()

        if not target_file:
            raise ValueError(
                "File replacement generation requires a target file."
            )

        title = self._safe_str(
            step.get("title")
        ).strip()

        description = self._safe_str(
            step.get("description")
            or step.get("text")
            or step.get("task")
            or step.get("instruction")
            or step.get("name")
        ).strip()

        execution_mode = self._safe_str(
            step.get("execution_mode")
        ).strip().lower()

        dependencies = step.get(
            "dependencies",
            [],
        )

        if not isinstance(
            dependencies,
            list,
        ):
            dependencies = []

        expected_output = self._safe_str(
            step.get("expected_output")
        ).strip()

        completion_criteria = step.get(
            "completion_criteria",
            [],
        )

        if not isinstance(
            completion_criteria,
            list,
        ):
            completion_criteria = []

        project_context = self._safe_str(
            context.get("project_context")
        ).strip()

        previous_results = context.get(
            "previous_results"
        )

        existing_content = self._safe_str(
            context.get("existing_content")
        )

        system_prompt = (
            "You are Nova's file implementation engine. "
            "Generate the complete replacement contents for the requested "
            "target file. "
            "Treat the task title, description, expected output, and "
            "completion criteria as REQUIREMENTS and SPECIFICATIONS, not as "
            "literal file content. "
            "You must IMPLEMENT those requirements by generating the actual "
            "contents of the target file. "
            "For a Python (.py) target, return valid runnable Python source "
            "code, never an English description of what the code should do. "
            "For any other target, generate the appropriate valid file "
            "format for that extension. "
            "If the specification is underspecified, choose the simplest "
            "reasonable implementation that satisfies it rather than "
            "returning the specification itself. "
            "Return only the raw file contents. "
            "Do not use Markdown fences. "
            "Do not add explanations before or after the file contents. "
            "Do not describe the code. "
            "The returned output will be written directly to disk as the "
            "entire file. "
            "Produce valid, complete, production-quality code appropriate "
            "for the requested task."
        )

        prompt_parts = [
            f"Target file: {target_file}",
        ]

        if title:
            prompt_parts.append(
                f"Implementation task: {title}"
            )

        if description:
            prompt_parts.append(
                f"Task description:\n{description}"
            )

        if project_context:
            prompt_parts.append(
                f"Project context:\n{project_context}"
            )

        if previous_results:
            prompt_parts.append(
                "Previous execution results:\n"
                + self._safe_str(previous_results)
            )

        if existing_content:
            prompt_parts.append(
                "Existing file contents:\n"
                + existing_content
            )

        user_prompt = "\n\n".join(
            part
            for part in prompt_parts
            if part
        )

        response = self._create_response(
            session_id=session_id,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        output = self._extract_response_text(
            response
        ).strip()

        if not output:
            raise RuntimeError(
                "AI file replacement generation returned empty content."
            )

        output = self._strip_code_fences(
            output
        )

        output = self._validate_generated_file_content(
            output
        )

        if not output.strip():
            raise RuntimeError(
                "AI file replacement generation produced no usable content."
            )

        return {
            "ok": True,
            "target_file": target_file,
            "content": output,
        }

    def _create_response(
        self,
        session_id,
        system_prompt,
        user_prompt,
    ):
        return model_gateway_service.responses_create(
            nova_username=(
                os.getenv("NOVA_DEFAULT_USERNAME")
                or "richard"
            ),
            nova_session_id=session_id,
            model=self.chat_model,
            input=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
        )

    def _strip_code_fences(
        self,
        output,
    ):
        text = self._safe_str(output).strip()

        if not text.startswith("```"):
            return text

        lines = text.splitlines()

        if (
            lines
            and lines[0].lstrip().startswith("```")
        ):
            lines = lines[1:]

        if (
            lines
            and lines[-1].strip() == "```"
        ):
            lines = lines[:-1]

        return "\n".join(lines).strip()

    def _extract_response_text(
        self,
        response,
    ):
        if isinstance(response, str):
            return response

        if isinstance(response, dict):
            output_text = response.get(
                "output_text"
            )

            if isinstance(output_text, str):
                return output_text

            output = response.get("output")

            if isinstance(output, list):
                parts = []

                for item in output:
                    if not isinstance(item, dict):
                        continue

                    content = item.get("content")

                    if not isinstance(content, list):
                        continue

                    for content_item in content:
                        if not isinstance(
                            content_item,
                            dict,
                        ):
                            continue

                        text = content_item.get("text")

                        if isinstance(text, str):
                            parts.append(text)

                if parts:
                    return "\n".join(parts)

        output_text = getattr(
            response,
            "output_text",
            None,
        )

        if isinstance(output_text, str):
            return output_text

        return ""








