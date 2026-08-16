class MemoryConsolidator:


    def __init__(self):
        self.long_term_memory = []


    def consolidate(
        self,
        messages,
        context=None,
    ):

        memories = []

        for message in messages:

            text = self._clean(
                message.get("text", "")
            )

            if self._is_valuable(text):

                memories.append(
                    {
                        "memory": text,
                        "type": self._classify(text),
                        "confidence": 0.8,
                    }
                )


        result = {
            "new_memories": memories,
            "count": len(memories),
            "context": context or {},
        }


        self.long_term_memory.extend(
            memories
        )

        return result



    def _clean(
        self,
        text,
    ):

        return str(text).strip()



    def _is_valuable(
        self,
        text,
    ):

        if len(text) < 20:
            return False


        ignore = [
            "hello",
            "hi",
            "thanks",
            "ok",
            "what is",
            "who are",
        ]


        lower = text.lower()

        for item in ignore:
            if lower.startswith(item):
                return False


        keywords = [
            "always",
            "remember",
            "prefer",
            "use",
            "build",
            "project",
            "goal",
            "important",
        ]


        return any(
            word in lower
            for word in keywords
        )



    def _classify(
        self,
        text,
    ):

        lower = text.lower()


        if "prefer" in lower:
            return "preference"


        if "goal" in lower:
            return "goal"


        if "project" in lower:
            return "project"


        return "fact"



    def get_memory(self):

        return self.long_term_memory