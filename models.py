"""외부 API 데이터 검증에 사용하는 Pydantic 모델을 정의한다."""

from datetime import datetime
from ipaddress import IPv4Address, IPv6Address

from pydantic import BaseModel, Field


class WeatherRecord(BaseModel):
    """시간대별 날씨 데이터의 타입과 범위를 검증한다."""

    time: datetime
    temperature: float = Field(ge=-100, le=100)
    precipitation_probability: int = Field(ge=0, le=100)


class CountryRecord(BaseModel):
    """국가 정보의 필수 문자열을 검증한다."""

    country: str = Field(min_length=1)
    capital: str = Field(min_length=1)
    region: str = Field(min_length=1)


class LocationRecord(BaseModel):
    """IP 기반 지역 정보와 좌표 범위를 검증한다."""

    ip: IPv4Address | IPv6Address
    city: str = Field(min_length=1)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)