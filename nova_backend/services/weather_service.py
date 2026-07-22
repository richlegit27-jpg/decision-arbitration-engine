import re
from datetime import datetime
from typing import Any

import requests


class WeatherService:

    GEOCODING_URL = (
        "https://geocoding-api.open-meteo.com/v1/search"
    )

    FORECAST_URL = (
        "https://api.open-meteo.com/v1/forecast"
    )

    SOURCE_URL = "https://open-meteo.com/en/docs"

    def __init__(self, timeout: int = 15):
        self.timeout = max(5, int(timeout or 15))

    def _weather_description(self, code: Any) -> str:
        try:
            value = int(code)
        except (TypeError, ValueError):
            return "unknown conditions"

        if value == 0:
            return "clear"
        if value == 1:
            return "mainly clear"
        if value == 2:
            return "partly cloudy"
        if value == 3:
            return "overcast"
        if value in {45, 48}:
            return "foggy"
        if value in {51, 53, 55, 56, 57}:
            return "drizzle"
        if value in {61, 63, 65, 66, 67}:
            return "rain"
        if value in {71, 73, 75, 77}:
            return "snow"
        if value in {80, 81, 82}:
            return "rain showers"
        if value in {85, 86}:
            return "snow showers"
        if value in {95, 96, 99}:
            return "thunderstorms"

        return "mixed conditions"

    def _clean_location(self, value: str) -> str:
        text = str(value or "").strip()

        text = re.sub(
            r"^(?:user|assistant)\s*:\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )

        text = re.sub(
            r"^(?:what(?:'s| is| will)?|how(?:'s| is)?|"
            r"tell me|show me|give me|will)\s+",
            "",
            text,
            flags=re.IGNORECASE,
        )

        text = re.sub(
            r"\b(?:current|latest|the)\b",
            " ",
            text,
            flags=re.IGNORECASE,
        )

        text = re.sub(r"['’]s$", "", text)
        text = re.sub(r"\s+", " ", text).strip(" ,?.-")

        return text[:100]

    def _location_from_text(self, value: str) -> str:
        text = str(value or "").strip()

        if not text:
            return ""

        possessive = re.search(
            r"\b([A-Z][A-Za-z.-]+"
            r"(?:\s+(?:BC|B\.C\.|British Columbia|"
            r"ON|Ontario|AB|Alberta))?)['’]s\s+"
            r"(?:weather|forecast)",
            text,
        )

        if possessive:
            return self._clean_location(
                possessive.group(1)
            )

        before_weather = re.search(
            r"(.+?)\s+(?:weather|forecast)\b",
            text,
            flags=re.IGNORECASE,
        )

        if before_weather:
            candidate = self._clean_location(
                before_weather.group(1)
            )

            candidate = re.sub(
                r"^.*?\b(?:in|for)\s+",
                "",
                candidate,
                flags=re.IGNORECASE,
            ).strip()

            if candidate:
                return candidate

        after_in = re.search(
            r"\b(?:in|for)\s+"
            r"([A-Za-z][A-Za-z .'-]{1,70}?)"
            r"(?=\s+(?:today|tomorrow|tonight|"
            r"at|around)|[?,.\n]|$)",
            text,
            flags=re.IGNORECASE,
        )

        if after_in:
            return self._clean_location(
                after_in.group(1)
            )

        return ""

    def _extract_location(
        self,
        query: str,
        context: str = "",
    ) -> str:
        location = self._location_from_text(query)

        if location:
            return location

        lines = str(context or "").splitlines()
        recent_lines = lines[-16:]

        user_lines = [
            line
            for line in reversed(recent_lines)
            if re.match(
                r"^\s*user\s*:",
                line,
                flags=re.IGNORECASE,
            )
        ]

        other_lines = [
            line
            for line in reversed(recent_lines)
            if line not in user_lines
        ]

        for line in user_lines + other_lines:
            location = self._location_from_text(line)

            if location:
                return location

        return ""

    def _extract_hour(self, query: str):
        match = re.search(
            r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b",
            str(query or ""),
            flags=re.IGNORECASE,
        )

        if not match:
            return None

        hour = int(match.group(1))
        minute = int(match.group(2) or 0)
        meridiem = match.group(3).lower()

        if hour == 12:
            hour = 0

        if meridiem == "pm":
            hour += 12

        return hour, minute

    def _geocode(self, location: str) -> dict:
        candidates = [location]

        short_location = location.split(",", 1)[0].strip()

        if (
            short_location
            and short_location.lower()
            != location.lower()
        ):
            candidates.append(short_location)

        results = []

        for candidate in candidates:
            response = requests.get(
                self.GEOCODING_URL,
                params={
                    "name": candidate,
                    "count": 5,
                    "language": "en",
                    "format": "json",
                },
                timeout=self.timeout,
            )

            response.raise_for_status()
            results = (
                (response.json() or {}).get("results")
                or []
            )

            if results:
                break

        if not results:
            return {}

        location_lower = location.lower()

        if (
            "bc" in location_lower
            or "british columbia" in location_lower
        ):
            for item in results:
                if (
                    str(item.get("admin1") or "").lower()
                    == "british columbia"
                ):
                    return item

        return results[0]

    def _forecast(self, latitude, longitude) -> dict:
        response = requests.get(
            self.FORECAST_URL,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "hourly": (
                    "temperature_2m,"
                    "apparent_temperature,"
                    "precipitation_probability,"
                    "precipitation,"
                    "weather_code,"
                    "wind_speed_10m"
                ),
                "daily": (
                    "weather_code,"
                    "temperature_2m_max,"
                    "temperature_2m_min,"
                    "precipitation_probability_max"
                ),
                "timezone": "auto",
                "forecast_days": 3,
            },
            timeout=self.timeout,
        )

        response.raise_for_status()
        return response.json() or {}

    def lookup(
        self,
        query: str,
        context: str = "",
    ) -> dict:
        question = str(query or "").strip()
        location_query = self._extract_location(
            question,
            context=context,
        )

        if not location_query:
            return {
                "ok": False,
                "query": question,
                "results": [],
                "body": "",
                "summary": "",
                "source_type": "open_meteo_weather",
                "error": "Weather location could not be resolved.",
            }

        try:
            place = self._geocode(location_query)

            if not place:
                raise ValueError(
                    f'Location not found: "{location_query}".'
                )

            forecast = self._forecast(
                place.get("latitude"),
                place.get("longitude"),
            )

            daily = forecast.get("daily") or {}
            hourly = forecast.get("hourly") or {}

            dates = daily.get("time") or []

            if not dates:
                raise ValueError("Forecast returned no dates.")

            query_lower = question.lower()
            day_reference = query_lower

            if not any(
                marker in query_lower
                for marker in (
                    "today",
                    "tomorrow",
                    "tonight",
                )
            ):
                for line in reversed(
                    str(context or "").splitlines()
                ):
                    line_lower = line.lower()

                    if any(
                        marker in line_lower
                        for marker in (
                            "today",
                            "tomorrow",
                            "tonight",
                        )
                    ):
                        day_reference = line_lower
                        break

            day_index = (
                1 if "tomorrow" in day_reference else 0
            )
            day_index = min(day_index, len(dates) - 1)
            target_date = dates[day_index]

            display_location = ", ".join(
                value
                for value in (
                    str(place.get("name") or "").strip(),
                    str(place.get("admin1") or "").strip(),
                    str(place.get("country") or "").strip(),
                )
                if value
            )

            requested_hour = self._extract_hour(question)

            if requested_hour:
                hour, minute = requested_hour
                target_time = (
                    f"{target_date}T{hour:02d}:00"
                )

                times = hourly.get("time") or []

                if target_time not in times:
                    raise ValueError(
                        "Requested hourly forecast is unavailable."
                    )

                index = times.index(target_time)

                temperature = (
                    hourly.get("temperature_2m") or []
                )[index]

                apparent = (
                    hourly.get("apparent_temperature") or []
                )[index]

                probability = (
                    hourly.get(
                        "precipitation_probability"
                    )
                    or []
                )[index]

                precipitation = (
                    hourly.get("precipitation") or []
                )[index]

                code = (
                    hourly.get("weather_code") or []
                )[index]

                wind = (
                    hourly.get("wind_speed_10m") or []
                )[index]

                display_hour = hour % 12 or 12
                meridiem = "PM" if hour >= 12 else "AM"
                label = (
                    f"{display_hour}:{minute:02d} "
                    f"{meridiem}"
                )

                description = self._weather_description(code)

                if (
                    float(probability or 0) >= 40
                    or float(precipitation or 0) > 0.1
                ):
                    umbrella = (
                        "Bring an umbrella."
                    )
                else:
                    umbrella = (
                        "An umbrella probably is not needed."
                    )

                summary = (
                    f"{display_location} at {label} on "
                    f"{target_date}: {description}, "
                    f"{float(temperature):.0f}°C, feels like "
                    f"{float(apparent):.0f}°C. "
                    f"Precipitation probability: "
                    f"{float(probability or 0):.0f}%. "
                    f"Expected precipitation: "
                    f"{float(precipitation or 0):.1f} mm. "
                    f"Wind: {float(wind or 0):.0f} km/h. "
                    f"{umbrella}"
                )

            else:
                high = (
                    daily.get("temperature_2m_max") or []
                )[day_index]

                low = (
                    daily.get("temperature_2m_min") or []
                )[day_index]

                probability = (
                    daily.get(
                        "precipitation_probability_max"
                    )
                    or []
                )[day_index]

                code = (
                    daily.get("weather_code") or []
                )[day_index]

                description = self._weather_description(code)

                summary = (
                    f"{display_location} forecast for "
                    f"{target_date}: {description}. "
                    f"High {float(high):.0f}°C, "
                    f"low {float(low):.0f}°C. "
                    f"Maximum precipitation probability: "
                    f"{float(probability or 0):.0f}%."
                )

            source = {
                "title": (
                    f"Open-Meteo forecast for "
                    f"{display_location}"
                ),
                "url": self.SOURCE_URL,
                "source": "open-meteo.com",
                "domain": "open-meteo.com",
                "snippet": summary,
                "score": 100.0,
            }

            return {
                "ok": True,
                "query": question,
                "results": [source],
                "body": summary,
                "summary": summary,
                "source_type": "open_meteo_weather",
                "location": {
                    "name": display_location,
                    "latitude": place.get("latitude"),
                    "longitude": place.get("longitude"),
                    "timezone": forecast.get("timezone"),
                },
                "error": "",
            }

        except Exception as exc:
            return {
                "ok": False,
                "query": question,
                "results": [],
                "body": "",
                "summary": "",
                "source_type": "open_meteo_weather",
                "error": str(exc),
            }
