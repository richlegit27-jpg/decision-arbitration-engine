class SkillRegistry:


    def __init__(self):
        self.skills = {}



    def register(
        self,
        name,
        description,
        handler,
    ):

        self.skills[name] = {
            "name": name,
            "description": description,
            "handler": handler,
            "enabled": True,
        }


        return self.skills[name]



    def get_skill(
        self,
        name,
    ):

        return self.skills.get(
            name
        )



    def list_skills(self):

        return [
            {
                "name": skill["name"],
                "description": skill["description"],
                "enabled": skill["enabled"],
            }
            for skill in self.skills.values()
        ]



    def find_skill(
        self,
        query,
    ):

        query = str(query).lower()

        matches = []

        for skill in self.skills.values():

            text = (
                skill["name"]
                + " "
                + skill["description"]
            ).lower()


            if query in text:
                matches.append(skill)


        return matches



    def execute(
        self,
        name,
        *args,
        **kwargs,
    ):

        skill = self.get_skill(name)

        if not skill:
            raise ValueError(
                f"Skill not found: {name}"
            )


        if not skill["enabled"]:
            raise RuntimeError(
                f"Skill disabled: {name}"
            )


        return skill["handler"](
            *args,
            **kwargs,
        )