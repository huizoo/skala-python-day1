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
    .env에 설정한 Open-Meteo, Countries.dev, ip-api의 JSON 응답

구현 내용:
    1. asyncio.gather()로 세 API를 동시에 수집한다.
    2. 필요한 필드를 추출하고 Pydantic v2 모델로 검증한다.
    3. 검증된 데이터를 CSV와 Parquet으로 저장하고 다시 읽는다.
    4. 두 파일 형식의 읽기·쓰기 시간을 측정하고 결과를 비교한다.

파일 구성:
    collector.py: 비동기 API 수집
    models.py: Pydantic 검증 모델
    transformer.py: 응답 필드 추출 및 레코드 변환
    storage.py: CSV·Parquet 저장, 재로딩 및 검증
    tests/test_models.py: Pydantic 모델 검증 테스트

변경 사항:
    한 파일에 작성했던 기능을 역할별 모듈로 분리하고,
    환경변수·API 응답·파일 처리 예외와 pytest 검증을 추가했다.

출력 결과:
    output/collected_data.csv
    output/collected_data.parquet
    형식별 읽기·쓰기 성능 측정 및 재로딩 검증 결과
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
        # asyncio.gather를 활용하여 3개의 API를 동시에 수집
        collected_data = asyncio.run(
            collect_all(
                get_required_env("OPEN_METEO_URL"),
                get_required_env("COUNTRIES_URL"),
                get_required_env("IP_API_URL"),
            )
        )

        # 필요한 필드를 추출하고 Pydantic 모델로 검증
        records = transform_records(collected_data)

        print("\n-------------------- Pydantic 검증 결과 --------------------")
        print(f"검증 완료: {len(records)}건")
        print("첫 번째 레코드:", records[0])
        print("마지막 레코드:", records[-1])

        # 검증된 동일 데이터를 CSV와 Parquet으로 저장
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

        # 저장한 두 파일을 다시 불러와 읽기 시간 측정
        (
            reloaded_csv,
            reloaded_parquet,
            csv_read_time,
            parquet_read_time,
        ) = reload_records(CSV_PATH, PARQUET_PATH)

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

        # 실제 수집 건수와 재로딩 데이터의 건수 및 컬럼 확인
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
        print(f"CSV     - 쓰기: {csv_write_time:.6f}초, 읽기: {csv_read_time:.6f}초")
        print(
            f"Parquet - 쓰기: {parquet_write_time:.6f}초, "
            f"읽기: {parquet_read_time:.6f}초"
        )

        # 측정 결과를 비교하여 더 빠른 파일 형식 확인
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
