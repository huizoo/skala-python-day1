"""Pydantic 모델의 정상 데이터와 오류 데이터를 검증한다."""

import pytest
from pydantic import ValidationError

from models import LocationRecord, WeatherRecord


def test_weather_record_valid() -> None:
    """정상적인 날씨 데이터가 검증을 통과하는지 확인한다."""
    weather = WeatherRecord.model_validate(
        {
            "time": "2026-07-20T00:00:00",
            "temperature": 23.2,
            "precipitation_probability": 40,
        }
    )

    assert weather.temperature == 23.2
    assert weather.precipitation_probability == 40


def test_weather_record_invalid_precipitation() -> None:
    """강수확률이 허용 범위를 벗어나면 검증에 실패하는지 확인한다."""
    with pytest.raises(ValidationError):
        WeatherRecord.model_validate(
            {
                "time": "2026-07-20T00:00:00",
                "temperature": 23.2,
                "precipitation_probability": 150,
            }
        )
    

def test_location_record_invalid_latitude() -> None:
    """위도가 허용 범위를 벗어나면 검증에 실패하는지 확인한다."""
    with pytest.raises(ValidationError):
        LocationRecord.model_validate(
            {
                "ip": "8.8.8.8",
                "city": "Ashburn",
                "latitude": 100,
                "longitude": -77.5,
            }
        )