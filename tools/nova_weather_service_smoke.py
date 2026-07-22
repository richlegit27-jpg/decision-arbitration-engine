from nova_backend.services.weather_service import (
    WeatherService,
)


def assert_true(name, condition):
    if not condition:
        raise AssertionError(f"{name} FAILED")

    print(f"PASS {name}")


class FakeWeatherService(WeatherService):

    def _geocode(self, location):
        return {
            "name": "Vancouver",
            "admin1": "British Columbia",
            "country": "Canada",
            "latitude": 49.25,
            "longitude": -123.12,
        }

    def _forecast(self, latitude, longitude):
        return {
            "timezone": "America/Vancouver",
            "daily": {
                "time": [
                    "2026-07-22",
                    "2026-07-23",
                ],
                "weather_code": [2, 3],
                "temperature_2m_max": [27, 29],
                "temperature_2m_min": [18, 20],
                "precipitation_probability_max": [
                    10,
                    6,
                ],
            },
            "hourly": {
                "time": [
                    "2026-07-23T19:00",
                ],
                "temperature_2m": [28],
                "apparent_temperature": [28],
                "precipitation_probability": [0],
                "precipitation": [0.0],
                "weather_code": [3],
                "wind_speed_10m": [8],
            },
        }


service = FakeWeatherService()

first = service.lookup(
    "What will Vancouver's weather be tomorrow?"
)

assert_true(
    "tomorrow_forecast_resolved",
    first.get("ok") is True
    and "2026-07-23" in first.get("body", ""),
)

second = service.lookup(
    "Will I need an umbrella around 7 PM?",
    context=(
        "user: What will Vancouver's weather be tomorrow?\n"
        "assistant: Vancouver forecast for tomorrow."
    ),
)

answer = second.get("body") or ""

assert_true(
    "followup_location_inherited",
    second.get("ok") is True
    and "Vancouver" in answer,
)

assert_true(
    "followup_day_inherited",
    "2026-07-23" in answer,
)

assert_true(
    "hourly_time_resolved",
    "7:00 PM" in answer,
)

assert_true(
    "precipitation_probability_reported",
    "Precipitation probability: 0%" in answer,
)

assert_true(
    "umbrella_guidance_reported",
    "umbrella probably is not needed"
    in answer.lower(),
)

from nova_backend.services.session_service import (
    SessionService,
)

belongs = SessionService._belongs_to_user

assert_true(
    "anonymous_session_continuity",
    belongs(None, {"user_id": ""}, "") is True,
)

assert_true(
    "anonymous_cannot_access_owned_session",
    belongs(None, {"user_id": "owner-a"}, "") is False,
)

assert_true(
    "authenticated_user_can_claim_unowned_session",
    belongs(None, {"user_id": ""}, "owner-a") is True,
)

assert_true(
    "different_owner_rejected",
    belongs(
        None,
        {"user_id": "owner-a"},
        "owner-b",
    ) is False,
)

print("\nNOVA WEATHER SERVICE SMOKE PASSED")
