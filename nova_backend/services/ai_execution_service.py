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
        ).strip()

        action = self._safe_str(
            step.get("action")
        ).strip().lower()

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

        response = model_gateway_service.responses_create(
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