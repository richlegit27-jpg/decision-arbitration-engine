# Nova tool trust boundary

## Canonical runtime

`ChatService` creates the runtime with `build_tool_runtime()`. The factory loads registered `NovaTool` implementations, then wires the service `ToolExecutor`, `ToolRegistry`, and `ToolBridge`. Chat dispatch and approval completion use that executor. The older module-level executor remains only as a compatibility surface and applies the shared risk policy; tool metadata endpoints read from the canonical service registry.

## Safety rules

- Write, destructive, and external-action tools require explicit approval. Missing approval does not authorize execution.
- File-system tool paths are resolved against `PythonRunnerService`'s configured sandbox and rejected if they escape it.
- Shell, terminal, Python script execution, and arbitrary process launch are blocked until Nova has an operating-system-enforced workspace sandbox.
- Web fetch requires an authenticated user, permits only public HTTP(S) targets, validates each redirect, and reports unsuccessful fetches as failures.
- Memory tools use the application-owned `MemoryService`, which scopes reads and writes to the server-authenticated owner.
- Pending approvals are process-local and scoped to both session and owner. They are not durable across worker restart and deployments with multiple workers need shared storage before relying on approvals across requests.
- Tool logs record tool identity, risk, timing, outcome, and error category; raw arguments and payloads are excluded.

## Known limitations

The project currently has no operating-system-enforced sandbox for arbitrary command or Python execution, so those tools are intentionally blocked. Web destination DNS is checked before each HTTP request and redirect, but the HTTP client performs its own DNS lookup; deployments requiring protection against DNS rebinding should pin validated destination addresses at connection time.
