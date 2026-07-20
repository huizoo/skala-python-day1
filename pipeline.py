"""
[Day 1 종합 실습] 데이터 수집 미니 파이프라인

코드 작성자:
    김희주

소속:
    광주 캠퍼스 4반 1조

실습 목적:
    세 개의 외부 API를 비동기로 수집하고 Pydantic v2로 검증한 뒤,
    CSV와 Parquet으로 저장해 읽기·쓰기 성능을 비교한다.

입력 데이터:
    Open-Meteo, Countries.dev, ip-api의 JSON 응답

주요 처리 과정:
    비동기 API 수집, 스키마 검증, 데이터 저장 및 재로딩,
    CSV와 Parquet의 읽기·쓰기 시간 측정

출력 결과:
    검증된 CSV·Parquet 파일과 형식별 성능 측정 결과
"""

import asyncio
import os
from pathlib import Path
from typing import Any
from time import perf_counter
import pandas as pd
from pydantic import ValidationError

from models import CountryRecord, LocationRecord, WeatherRecord

import httpx
from dotenv import load_dotenv

ENV_PATH = Path(__file__).with_name(".env")
load_dotenv(ENV_PATH)

OPEN_METEO_URL = os.environ["OPEN_METEO_URL"]
COUNTRIES_URL = os.environ["COUNTRIES_URL"]
IP_API_URL = os.environ["IP_API_URL"]

OUTPUT_DIR = Path(__file__).with_name("output")
CSV_PATH = OUTPUT_DIR / "collected_data.csv"
PARQUET_PATH = OUTPUT_DIR / "collected_data.parquet"

async def fetch_json(
    client: httpx.AsyncClient,
    source: str,
    url: str,
) -> tuple[str, dict[str, Any]]:
    """API를 호출하고 출처명과 JSON 응답을 반환한다."""
    response = await client.get(url)
    response.raise_for_status()

    data = response.json()

    if not isinstance(data, dict):
        raise TypeError(f"{source} 응답이 JSON 객체 형식이 아닙니다.")
    
    print(f"{source} 수집 완료: HTTP {response.status_code}")
    return source, data


async def collect_all() -> dict[str, dict[str, Any]]:
    """세 개의 API를 동시에 호출하고 출처별 응답을 반환한다."""
    timeout = httpx.Timeout(20.0)

    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=True,
    ) as client:
        results = await asyncio.gather(
            fetch_json(client, "Open-Meteo", OPEN_METEO_URL),
            fetch_json(client, "Countries.dev", COUNTRIES_URL),
            fetch_json(client, "ip-api", IP_API_URL),
        )

    return dict(results)


if __name__ == "__main__":
    try:
        collected_data = asyncio.run(collect_all())

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

        records = [
            {
                **country_values,
                **location_values,
                **weather_record.model_dump(mode="json"),
            }
            for weather_record in weather_records
        ]

        print("\n-------------------- Pydantic 검증 결과 --------------------")
        print(f"검증 완료: {len(records)}건")
        print("첫 번째 레코드:", records[0])
        print("마지막 레코드:", records[-1])


        OUTPUT_DIR.mkdir(exist_ok=True)

        data_frame = pd.DataFrame(records)

        csv_write_start = perf_counter()
        data_frame.to_csv(
            CSV_PATH,
            index=False,
            encoding="utf-8-sig",
        )
        csv_write_time = perf_counter() - csv_write_start

        parquet_write_start = perf_counter()
        data_frame.to_parquet(
            PARQUET_PATH,
            index=False,
        )
        parquet_write_time = perf_counter() - parquet_write_start

        print("\n-------------------- 파일 저장 결과 --------------------")
        print(f"CSV 저장 완료: {CSV_PATH.name}")
        print(f"Parquet 저장 완료: {PARQUET_PATH.name}")
        print(f"저장 데이터: {len(data_frame)}행 × {len(data_frame.columns)}열")

        print("\n-------------------- 쓰기 성능 비교 --------------------")
        print(f"CSV 쓰기 시간: {csv_write_time:.6f}초")
        print(f"Parquet 쓰기 시간: {parquet_write_time:.6f}초")

        csv_read_start = perf_counter()
        reloaded_csv = pd.read_csv(CSV_PATH)
        csv_read_time = perf_counter() - csv_read_start

        parquet_read_start = perf_counter()
        reloaded_parquet = pd.read_parquet(PARQUET_PATH)
        parquet_read_time = perf_counter() - parquet_read_start

        required_columns = {
            "country",
            "capital",
            "region",
            "ip",
            "city",
            "latitude",
            "longitude",
            "time",
            "temperature",
            "precipitation_probability",
        }

        print("\n-------------------- 재로딩 검증 시작 --------------------")

        assert len(records) == 72, "3일간 시간대별 데이터는 72건이어야 합니다."
        
        assert len(reloaded_csv) == len(data_frame), "CSV의 데이터 개수가 다릅니다."
        assert len(reloaded_parquet) == len(data_frame), "Parquet의 데이터 개수가 다릅니다."

        assert set(reloaded_csv.columns) == set(data_frame.columns), "CSV의 컬럼이 원본과 다릅니다."
        assert set(reloaded_parquet.columns) == set(data_frame.columns), "Parquet의 컬럼이 원본과 다릅니다."
        
        assert required_columns.issubset(reloaded_csv.columns), "CSV에 필수 컬럼이 없습니다."
        assert required_columns.issubset(reloaded_parquet.columns), "Parquet에 필수 컬럼이 없습니다."

        print("CSV·Parquet 데이터 개수 확인 완료")
        print("CSV·Parquet 컬럼 확인 완료")
        print("-------------------- 재로딩 검증 통과 --------------------")

        print("\n-------------------- 읽기 성능 비교 --------------------")
        print(f"CSV 읽기 시간: {csv_read_time:.6f}초")
        print(f"Parquet 읽기 시간: {parquet_read_time:.6f}초")

        print("\n-------------------- 전체 성능 측정 결과 --------------------")
        print(
            f"CSV     - 쓰기: {csv_write_time:.6f}초, "
            f"읽기: {csv_read_time:.6f}초"
        )
        print(
            f"Parquet - 쓰기: {parquet_write_time:.6f}초, "
            f"읽기: {parquet_read_time:.6f}초"
        )

    except ValidationError as error:
        print("\nPydantic 검증 오류")

        for detail in error.errors():
            field = ".".join(str(item) for item in detail["loc"])
            print(f"- {field}: {detail['msg']}")

    except httpx.HTTPError as error:
        print(f"API 요청 오류: {error}")

    except (TypeError, ValueError) as error:
        print(f"응답 처리 오류: {error}")
