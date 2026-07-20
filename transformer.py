"""수집한 API 응답을 검증하고 저장 가능한 레코드로 변환한다."""

from typing import Any

from models import CountryRecord, LocationRecord, WeatherRecord


def transform_records(
    collected_data: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """세 API 응답을 검증하고 시간대별 평면 레코드로 변환한다."""
    weather_data = collected_data["Open-Meteo"]
    country_data = collected_data["Countries.dev"]
    location_data = collected_data["ip-api"]

    hourly_data = weather_data["hourly"]

    country_record = CountryRecord.model_validate(
        {
            "country": country_data["name"],
            "capital": country_data["capital"],
            "region": country_data["region"],
        }
    )

    location_record = LocationRecord.model_validate(
        {
            "ip": location_data["query"],
            "city": location_data["city"],
            "latitude": location_data["lat"],
            "longitude": location_data["lon"],
        }
    )

    weather_records = [
        WeatherRecord.model_validate(
            {
                "time": time,
                "temperature": temperature,
                "precipitation_probability": precipitation,
            }
        )
        for time, temperature, precipitation in zip(
            hourly_data["time"],
            hourly_data["temperature_2m"],
            hourly_data["precipitation_probability"],
            strict=True,
        )
    ]

    country_values = country_record.model_dump(mode="json")
    location_values = location_record.model_dump(mode="json")

    return [
        {
            **country_values,
            **location_values,
            **weather_record.model_dump(mode="json"),
        }
        for weather_record in weather_records
    ]