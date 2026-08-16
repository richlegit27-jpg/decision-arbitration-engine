class MemoryIntelligence:


    def __init__(self):
        self.ignore_patterns = [
            "hi",
            "hello",
            "hey",
            "what is my name",
            "test",
        ]


    def should_store(self, text):

        if not text:
            return False

        value = text.lower().strip()

        for item in self.ignore_patterns:
            if value == item:
                return False

        return len(value) > 5



    def extract_memory(self, text):

        if not self.should_store(text):
            return None

        value = text.strip()

        triggers = [
            "remember that",
            "always",
            "i prefer",
            "i like",
            "my goal is",
            "nova uses",
        ]

        lower = value.lower()

        for trigger in triggers:
            if trigger in lower:

                return {
                    "type": "preference",
                    "content": value,
                    "confidence": 0.9,
                }

        return None



    def rank(
        self,
        memories,
        query,
    ):

        if not memories:
            return []


        query = query.lower()

        scored = []

        for memory in memories:

            text = str(
                memory.get("content","")
            ).lower()

            score = 0

            for word in query.split():

                if word in text:
                    score += 1


            scored.append(
                (
                    score,
                    memory
                )
            )


        scored.sort(
            key=lambda x:x[0],
            reverse=True
        )


        return [
            item[1]
            for item in scored[:5]
        ]