class ChatResponsePolicyService:

    def build_response_policy(self, user_text: str = "", decision=None) -> dict:
        """
        Central response policy layer.

        This does NOT answer the user.
        It tells Nova HOW to answer:
        - short/direct
        - SMFF/full-file mode
        - debugging mode
        - frustrated user mode
        - latest/news mode
        - command-first mode
        """

        decision = decision if isinstance(decision, dict) else {}
        text = str(user_text or "").strip()
        lower = text.lower()

        policy = {
            "mode": "normal",
            "answer_length": "normal",
            "tone": "direct",
            "needs_steps": False,
            "needs_full_file": False,
            "needs_commands": False,
            "needs_latest": False,
            "needs_debug": False,
            "user_frustrated": False,
            "avoid_examples": False,
            "prefer_power_shell": True,
            "instruction": "",
        }

        # -----------------------------
        # User frustration / urgency
        # -----------------------------
        frustration_markers = [
            "fuck",
            "wtf",
            "this sucks",
            "waste of time",
            "madness",
            "annoying",
            "broken again",
            "i don't know what to do",
            "im lost",
            "i'm lost",
        ]

        if any(marker in lower for marker in frustration_markers):
            policy["user_frustrated"] = True
            policy["tone"] = "calm_direct"
            policy["answer_length"] = "short"
            policy["needs_steps"] = True

            policy["instruction"] += (
                "User is frustrated. Do not lecture. Do not explain feelings. "
                "Give the fix first. Use short confident language. "
                "One path forward only. Maximum 5 lines unless full code is requested.\n"
            )

        # -----------------------------
        # SMFF / full-file mode
        # -----------------------------
        smff_markers = [
            "smff",
            "full file",
            "whole file",
            "give me the whole",
            "full replacement",
            "replace the whole",
        ]

        if any(marker in lower for marker in smff_markers):
            policy["mode"] = "smff"
            policy["needs_full_file"] = True
            policy["answer_length"] = "full"
            policy["avoid_examples"] = True
            policy["instruction"] += (
                "User wants SMFF/full-file style. Provide complete replacement code "
                "or a complete helper block with exact file path and anchor. "
                "Avoid tiny partial snippets unless the user only pasted a small block.\n"
            )

        # -----------------------------
        # Debugging mode
        # -----------------------------
        debug_markers = [
            "error",
            "traceback",
            "syntaxerror",
            "indentationerror",
            "taberror",
            "uncaught",
            "404",
            "500",
            "not found",
            "failed to load",
            "broken",
            "compile",
        ]

        if any(marker in lower for marker in debug_markers):
            policy["needs_debug"] = True
            policy["needs_steps"] = True
            policy["needs_commands"] = True
            policy["answer_length"] = "short"
            policy["instruction"] += (
                "User is debugging. Identify the root cause first, then give the exact "
                "replacement or exact command. Do not wander.\n"
            )

        # -----------------------------
        # Next-step mode
        # -----------------------------
        next_markers = [
            "next",
            "what now",
            "what next",
            "go",
            "continue",
            "keep going",
        ]

        if lower in next_markers:
            policy["mode"] = "next_step"
            policy["needs_steps"] = True
            policy["answer_length"] = "ultra_short"
            policy["instruction"] += (
                "User said next. Reply with ONE concrete next action only. "
                "No explanation. No menu. No markdown essay. Maximum 3 short lines.\n"
            )

        # -----------------------------
        # Latest/news mode
        # -----------------------------
        latest_markers = [
            "latest",
            "fresh",
            "current",
            "right now",
            "news",
            "update",
        ]

        if any(marker in lower for marker in latest_markers):
            policy["needs_latest"] = True
            policy["instruction"] += (
                "User wants current information. Prefer fresh web/search route when available. "
                "Answer in words first, then sources if useful.\n"
            )

        # -----------------------------
        # PowerShell / command mode
        # -----------------------------
        command_markers = [
            "powershell",
            "command",
            "run this",
            "compile",
            "restart",
            "test",
        ]

        if any(marker in lower for marker in command_markers):
            policy["needs_commands"] = True
            policy["prefer_power_shell"] = True
            policy[
                "instruction"
            ] += "Use PowerShell commands when commands are needed.\n"

        # -----------------------------
        # User dislikes examples
        # -----------------------------
        no_example_markers = [
            "no examples",
            "don't give examples",
            "dont give examples",
            "just the code",
            "only the code",
        ]

        if any(marker in lower for marker in no_example_markers):
            policy["avoid_examples"] = True
            policy[
                "instruction"
            ] += "Avoid examples. Give the exact needed code or action only.\n"

        return policy
