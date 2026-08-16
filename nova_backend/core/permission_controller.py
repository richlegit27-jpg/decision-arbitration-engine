class PermissionController:


    def __init__(self):

        self.rules = {
            "read_file": "allow",
            "search": "allow",
            "analyze_code": "allow",

            "write_file": "approval",
            "delete_file": "approval",
            "run_command": "approval",
        }



    def check(
        self,
        action,
        context=None,
    ):

        context = context or {}

        level = self.rules.get(
            action,
            "approval",
        )


        result = {
            "action": action,
            "permission": level,
            "approved": False,
            "reason": "",
        }


        if level == "allow":

            result["approved"] = True
            result["reason"] = (
                "Safe operation"
            )


        elif level == "approval":

            result["reason"] = (
                "User confirmation required"
            )


        return result



    def add_rule(
        self,
        action,
        permission,
    ):

        self.rules[action] = permission