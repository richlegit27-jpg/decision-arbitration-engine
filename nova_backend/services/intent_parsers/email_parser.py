import re


class CalendarParser:
    """
    Converts chat → calendar event
    """

    def parse(self, text: str):
        text = (text or "").strip()

        title = "Event"

        # crude time detection
        time_match = re.search(r"(\d{1,2}(:\d{2})?\s*(am|pm)?)", text, re.I)
        time = time_match.group(1) if time_match else None

        if "meeting" in text.lower():
            title = "Meeting"

        return {
            "title": title,
            "time": time,
            "description": text
        }