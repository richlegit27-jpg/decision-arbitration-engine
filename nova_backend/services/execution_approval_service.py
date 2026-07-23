class ExecutionApprovalService:

    APPROVED_STATUSES = {
        "approved",
        "granted",
        "allowed",
    }

    def _clean(self, value):
        return str(value or "").strip().lower()

    def requires_approval(self, step):
        if not isinstance(step, dict):
            return False

        return bool(
            step.get("requires_approval")
            or step.get("approval_required")
        )

    def is_approved(self, step):
        if not isinstance(step, dict):
            return False

        if step.get("approved") is True:
            return True

        status = self._clean(
            step.get("approval_status")
        )

        if status in self.APPROVED_STATUSES:
            return True

        approval = step.get("approval")

        if isinstance(approval, dict):
            if approval.get("approved") is True:
                return True

            nested_status = self._clean(
                approval.get("status")
            )

            if (
                nested_status
                in self.APPROVED_STATUSES
            ):
                return True

        return False

    def evaluate(self, step):
        required = self.requires_approval(
            step
        )

        approved = (
            self.is_approved(step)
            if required
            else True
        )

        return {
            "required": required,
            "approved": approved,
            "waiting": (
                required
                and not approved
            ),
            "reason": (
                "Approval required before execution."
                if required and not approved
                else ""
            ),
        }