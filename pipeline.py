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
from pydantic import ValidationError

from collector import collect_all
from storage import reload_records, save_records, validate_reloaded
from transformer import transform_records

import httpx
from dotenv import load_dotenv

ENV_PATH = Path(__file__).with_name(".env")
load_dotenv(ENV_PATH)

def get_required_env(name: str) -> str:
    """필수 환경변수가 없거나 비어 있으면 오류를 발생시킨다."""
    value = os.getenv(name)

    if not value:
        raise ValueError(f"필수 환경변수가 없습니다: {name}")

    return value

OUTPUT_DIR = Path(__file__).with_name("output")
CSV_PATH = OUTPUT_DIR / "collected_data.csv"
PARQUET_PATH = OUTPUT_DIR / "collected_data.parquet"

if __name__ == "__main__":
    try:
        collected_data = asyncio.run(
            collect_all(
                get_required_env("OPEN_METEO_URL"),
                get_required_env("COUNTRIES_URL"),
                get_required_env("IP_API_URL")
            )
        )

        records = transform_records(collected_data)

        print("\n-------------------- Pydantic 검증 결과 --------------------")
        print(f"검증 완료: {len(records)}건")
        print("첫 번째 레코드:", records[0])
        print("마지막 레코드:", records[-1])

        data_frame, csv_write_time, parquet_write_time = save_records(
            records,
            CSV_PATH,
            PARQUET_PATH,
        )

        

        print("\n-------------------- 파일 저장 결과 --------------------")
        print(f"CSV 저장 완료: {CSV_PATH.name}")
        print(f"Parquet 저장 완료: {PARQUET_PATH.name}")
        print(f"저장 데이터: {len(data_frame)}행 × {len(data_frame.columns)}열")

        print("\n-------------------- 쓰기 성능 비교 --------------------")
        print(f"CSV 쓰기 시간: {csv_write_time:.6f}초")
        print(f"Parquet 쓰기 시간: {parquet_write_time:.6f}초")


        (
            reloaded_csv,
            reloaded_parquet,
            csv_read_time,
            parquet_read_time,
        ) = reload_records(
            CSV_PATH,
            PARQUET_PATH
        )


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
        
        validate_reloaded(
            data_frame,
            reloaded_csv,
            reloaded_parquet,
            required_columns,
        )

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

        if csv_write_time < parquet_write_time:
            faster_write_format = "CSV"
        else:
            faster_write_format = "Parquet"

        if csv_read_time < parquet_read_time:
            faster_read_format = "CSV"
        else:
            faster_read_format = "Parquet"

        print("\n-------------------- 성능 비교 분석 --------------------")
        print(f"쓰기 속도가 더 빠른 형식: {faster_write_format}")
        print(f"읽기 속도가 더 빠른 형식: {faster_read_format}")


    except ValidationError as error:
        print("\nPydantic 검증 오류")

        for detail in error.errors():
            field = ".".join(str(item) for item in detail["loc"])
            print(f"- {field}: {detail['msg']}")

    except httpx.HTTPError as error:
        print(f"API 요청 오류: {error}")

    except KeyError as error:
        print(f"필수 응답 필드가 없습니다: {error}")
    
    except OSError as error:
        print(f"파일 처리 오류: {error}")

    except (TypeError, ValueError) as error:
        print(f"응답 처리 오류: {error}")
