class ResponseMojibakeCleanupService:


    def clean_text(self, value):

        value = str(value or "")

        try:
            if "â" in value or "Ã" in value:
                value = (
                    value.encode("latin1")
                    .decode("utf-8")
                )
        except Exception:
            pass


        replacements = {
            "â€™": "'",
            "â€˜": "'",
            "â€œ": '"',
            "â€": '"',
            "â€\x9d": '"',

            "â€“": "-",
            "â€”": "-",
            "â€¦": "...",

            "â": "",
            "Ã": "",

            "it?s": "it's",
            "It?s": "It's",
        }


        for bad, good in replacements.items():
            value = value.replace(
                bad,
                good,
            )


        return value


    def cleanup(self, value):
        return self.clean_text(value)



    def clean_obj(self, obj):

        if isinstance(obj, str):
            return self.clean_text(obj)


        if isinstance(obj, list):
            return [
                self.clean_obj(item)
                for item in obj
            ]


        if isinstance(obj, dict):
            return {
                key: self.clean_obj(value)
                for key, value in obj.items()
            }


        return obj



    def clean_response(self, result):

        try:
            return self.clean_obj(result)

        except Exception:
            return result