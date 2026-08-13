
class AutoFixService:

    def __init__(self, chat_service):
        self.chat_service = chat_service

    def execute_file_fix(
        self,
        user_text: str,
        session_id: str,
        attachments=None,
    ) -> dict:


        print("AUTO_FIX_FILE_HIT:", user_text)

        import os
        import time
        import py_compile
        import shutil
        import textwrap
        import traceback
        import re

        attachments = attachments or []

        user_text = self.chat_service.safe_str(user_text)

        path = self.chat_service._guess_path_from_text(user_text)

        if not path:
            assistant_text = (
                "Auto-fix failed.\n\n"
                "Reason: no file path detected.\n\n"
                "Send like:\n"
                "fix this file C:\\Users\\Owner\\nova\\path\\file.py\n"
                "error: paste the traceback"
            )

            assistant_msg = self.chat_service._build_assistant_message(text=assistant_text)

            return self.chat_service._finalize_response(
                session_id=session_id,
                user_text=user_text,
                user_msg=self.chat_service._build_user_message(user_text),
                assistant_msg=assistant_msg,
                decision={"route": "auto_fix_failed"},
            )

        file_path = path.strip()

        # NOVA_AUTO_FIX_PLACEHOLDER_PATH_GUARD_20260624
        # Refuse the example path before auto-fix tries to read it.
        normalized_file_path = file_path.replace("/", "\\").strip().lower()
        placeholder_path_values = {
            "c:\\users\\owner\\nova\\path\\file.py",
            "\\nova\\path\\file.py",
            "\\path\\file.py",
        }

        if (
            not file_path
            or normalized_file_path.endswith("\\path\\file.py")
            or normalized_file_path in placeholder_path_values
            or "\\nova\\path\\" in normalized_file_path
        ):
            assistant_text = (
                "That is the example path, not a real file.\n\n"
                "Send the real file path and exact error.\n\n"
                "Example:\n"
                "fix this file C:\\Users\\Owner\\nova\\app.py\n"
                "error: paste the traceback"
            )

            assistant_msg = self.chat_service._build_assistant_message(text=assistant_text)

            return self.chat_service._finalize_response(
                session_id=session_id,
                user_text=user_text,
                user_msg=self.chat_service._build_user_message(user_text),
                assistant_msg=assistant_msg,
                decision={"route": "auto_fix_placeholder_path"},
            )

        pending_fix_mode = (
            self.chat_service._get_session_meta(session_id, "pending_fix_mode") or "file"
        )

        if "_process_execution_command" in user_text:
            pending_fix_mode = "function"
            self.chat_service._set_session_meta(
                session_id,
                "pending_fix_mode",
                "function",
            )
            self.chat_service._set_session_meta(
                session_id,
                "pending_fix_func_name",
                "_process_execution_command",
            )

        traceback_func_match = re.findall(
            r"in\s+([A-Za-z_][A-Za-z0-9_]*)",
            user_text,
        )
        traceback_func_name = traceback_func_match[-1] if traceback_func_match else ""

        if pending_fix_mode == "function" and traceback_func_name:
            self.chat_service._set_session_meta(
                session_id, "pending_fix_func_name", traceback_func_name
            )

        if "```" in file_path:
            file_path = file_path.split("```", 1)[0].strip()

        if "python" in file_path.lower():
            file_path = file_path.split("python", 1)[0].strip()

        code_match = re.search(
            r"```(?:python|py)?\s*(.*?)```",
            user_text,
            re.IGNORECASE | re.DOTALL,
        )

        raw_code = code_match.group(1).strip() if code_match else ""

        if not raw_code:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    raw_code = f.read()
            except Exception as e:
                assistant_text = (
                    "Auto-fix failed.\n\n"
                    f"File: {file_path}\n\n"
                    f"Reason: could not read file: {type(e).__name__}: {self.chat_service.safe_str(e)}"
                )

                assistant_msg = self.chat_service._build_assistant_message(text=assistant_text)

                return self.chat_service._finalize_response(
                    session_id=session_id,
                    user_text=user_text,
                    user_msg=self.chat_service._build_user_message(user_text),
                    assistant_msg=assistant_msg,
                    decision={"route": "auto_fix_read_failed"},
                )

        if pending_fix_mode != "function" and len(raw_code) > 12000:
            assistant_text = (
                "Auto-fix paused.\n\n"
                f"File:\n{file_path}\n\n"
                "Reason: file is too large for safe whole-file auto-fix.\n\n"
                "Use a targeted function, pasted block, or traceback instead."
            )

            assistant_msg = self.chat_service._build_assistant_message(text=assistant_text)

            return self.chat_service._finalize_response(
                session_id=session_id,
                user_text=user_text,
                user_msg=self.chat_service._build_user_message(user_text),
                assistant_msg=assistant_msg,
                decision={"route": "auto_fix_too_large"},
            )

        if pending_fix_mode == "function":
            func_name = (
                self.chat_service._get_session_meta(session_id, "pending_fix_func_name") or ""
            )

            pattern = rf"(def\s+{re.escape(func_name)}\s*\(.*?\):\n(?:\s+.*\n)*)"
            match = re.search(pattern, raw_code, re.DOTALL)
            extracted_function = match.group(1) if match else raw_code

            fix_prompt = (
                "You are fixing a Python function.\n"
                "Return ONLY the corrected function.\n"
                "Do NOT return the full file.\n"
                "No markdown. No explanation.\n\n"
                f"ERROR CONTEXT:\n{user_text}\n\n"
                f"TARGET FUNCTION:\n{func_name}\n\n"
                "FUNCTION CODE:\n"
                f"{extracted_function}\n\n"
                "Fix the root cause of the error. Do not rewrite unrelated logic."
            )
        else:
            fix_prompt = (
                "You are fixing a Python file.\n"
                "Return ONLY the complete corrected Python file.\n"
                "No markdown. No explanation. No code fences.\n\n"
                f"ERROR CONTEXT:\n{user_text}\n\n"
                f"FILE PATH:\n{file_path}\n\n"
                "CURRENT FILE CONTENT:\n"
                f"{raw_code}\n\n"
                "Fix the root cause of the error. Preserve architecture."
            )

        try:
            model_response = responses_create(
                nova_username=(
                    getattr(self, "username", None)
                    or os.getenv("NOVA_DEFAULT_USERNAME")
                    or "richard"
                ),
                nova_session_id=session_id,
                model=self.model,
                input=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert Python repair engine. "
                            "Preserve existing architecture. "
                            "Fix only what is necessary. "
                            "Return only the corrected code requested by the user prompt."
                        ),
                    },
                    {
                        "role": "user",
                        "content": fix_prompt,
                    },
                ],
            )

            fixed_code = self.chat_service.safe_str(model_response.output_text).strip()

            if fixed_code.startswith("```"):
                fixed_code = re.sub(
                    r"^```(?:python|py)?\s*", "", fixed_code, flags=re.IGNORECASE
                )
                fixed_code = re.sub(r"\s*```$", "", fixed_code).strip()

            if not fixed_code:
                raise ValueError("model returned empty fixed code")

        except Exception as e:
            error_text = self.chat_service.safe_str(e)
            error_name = type(e).__name__
            lowered_error = error_text.lower()

            if (
                "ratelimiterror" in error_name.lower()
                or "insufficient_quota" in lowered_error
                or "exceeded your current quota" in lowered_error
            ):
                assistant_text = (
                    "Auto-fix paused: OpenAI quota unavailable.\n\n"
                    f"File: {file_path}\n\n"
                    "Nova kept the failure context safe. "
                    "Fix generation can resume after API quota is available."
                )

                route = "auto_fix_quota_paused"

            else:
                assistant_text = (
                    "Auto-fix failed.\n\n"
                    f"File: {file_path}\n"
                    f"Reason: model fix failed: {error_name}: {error_text}"
                )

                route = "auto_fix_model_failed"

            assistant_msg = self.chat_service._build_assistant_message(text=assistant_text)

            return self.chat_service._finalize_response(
                session_id=session_id,
                user_text=user_text,
                user_msg=self.chat_service._build_user_message(user_text),
                assistant_msg=assistant_msg,
                decision={"route": route},
            )

        backup_path = None

        # =============================
        # SAVE AS PENDING FIX (NO WRITE)
        # =============================

        try:
            fixed_code = self._normalize_python_indentation(
                fixed_code
            )

            self.chat_service._update_working_state(
                session_id,
                {
                    "pending_fix_file_path": file_path,
                    "pending_fix_code": fixed_code,
                },
            )

            self.chat_service._set_session_meta(
                session_id,
                "pending_fix_mode",
                pending_fix_mode,
            )

            if pending_fix_mode == "function":
                self.chat_service._set_session_meta(
                    session_id,
                    "pending_fix_func_name",
                    self.chat_service._get_session_meta(session_id, "pending_fix_func_name") or "",
                )

            assistant_text = (
                "Auto-fix prepared.\n\n"
                f"File:\n{file_path}\n\n"
                "Preview of fix:\n"
                "```python\n"
                f"{fixed_code[:2000]}\n"
                "```\n\n"
                "Fix is ready but not applied.\n\n"
                "Say `apply fix` to write it."
            )

            assistant_msg = self.chat_service._build_assistant_message(text=assistant_text)

            return self.chat_service._finalize_response(
                session_id=session_id,
                user_text=user_text,
                user_msg=self.chat_service._build_user_message(user_text),
                assistant_msg=assistant_msg,
                decision={
                    "route": "auto_fix_prepare",
                    "pending_fix_mode": pending_fix_mode,
                },
            )

        except Exception as e:
            assistant_text = (
                "Auto-fix failed.\n\n"
                f"File: {file_path}\n"
                f"Error: {type(e).__name__}: {self.chat_service.safe_str(e)}"
            )

            assistant_msg = self.chat_service._build_assistant_message(text=assistant_text)

            return self.chat_service._finalize_response(
                session_id=session_id,
                user_text=user_text,
                user_msg=self.chat_service._build_user_message(user_text),
                assistant_msg=assistant_msg,
                decision={"route": "auto_fix_error"},
            )

        except Exception as e:
            assistant_text = (
                "Auto-fix failed.\n\n"
                f"File: {file_path}\n"
                f"Error: {type(e).__name__}: {self.chat_service.safe_str(e)}"
            )

            assistant_msg = self.chat_service._build_assistant_message(text=assistant_text)

            return self.chat_service._finalize_response(
                session_id=session_id,
                user_text=user_text,
                user_msg=self.chat_service._build_user_message(user_text),
                assistant_msg=assistant_msg,
                decision={"route": "auto_fix_error"},
            )

            compile_ok = True
            compile_output = ""

            try:
                py_compile.compile(file_path, doraise=True)
            except Exception:
                compile_ok = False
                compile_output = traceback.format_exc().strip()

            assistant_text = (
                "Auto-fix applied.\n\n"
                f"File: {file_path}\n"
                f"Backup: {backup_path or 'none'}\n\n"
                "Fix:\n"
                "- normalized indentation\n"
                "- replaced tabs with 4 spaces\n\n"
                "Result:\n"
                "```python\n"
                f"{fixed_code.strip()}\n"
                "```\n\n"
                f"Compile check: {'passed' if compile_ok else 'failed'}"
            )

            if compile_output:
                assistant_text += f"\n\n{compile_output}"

            return {
                "assistant_message": {"text": assistant_text},
                "session": self._get_session_payload(session_id),
                "ok": True,
            }

        except Exception as e:
            assistant_text = "Auto-fix failed.\n\n" f"File: {file_path}\n" f"Error: {e}"

            return {
                "assistant_message": {"text": assistant_text},
                "session": self._get_session_payload(session_id),
                "ok": False,
            }






