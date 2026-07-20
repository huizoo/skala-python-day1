"""CSV와 Parquet 파일의 저장, 재로딩 및 검증 기능을 제공한다."""

from pathlib import Path
from time import perf_counter
from typing import Any

import pandas as pd


def save_records(
    records: list[dict[str, Any]],
    csv_path: Path,
    parquet_path: Path,
) -> tuple[pd.DataFrame, float, float]:
    """동일한 데이터를 CSV와 Parquet으로 저장하고 시간을 반환한다."""
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    data_frame = pd.DataFrame(records)

    csv_start = perf_counter()
    data_frame.to_csv(
        csv_path,
        index=False,
        encoding="utf-8-sig",
    )
    csv_write_time = perf_counter() - csv_start

    parquet_start = perf_counter()
    data_frame.to_parquet(
        parquet_path,
        index=False,
    )
    parquet_write_time = perf_counter() - parquet_start

    return data_frame, csv_write_time, parquet_write_time


def reload_records(
    csv_path: Path,
    parquet_path: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, float, float]:
    """CSV와 Parquet을 다시 읽고 각각의 읽기 시간을 반환한다."""
    csv_start = perf_counter()
    reloaded_csv = pd.read_csv(csv_path)
    csv_read_time = perf_counter() - csv_start

    parquet_start = perf_counter()
    reloaded_parquet = pd.read_parquet(parquet_path)
    parquet_read_time = perf_counter() - parquet_start

    return (
        reloaded_csv,
        reloaded_parquet,
        csv_read_time,
        parquet_read_time,
    )


def validate_reloaded(
    original: pd.DataFrame,
    reloaded_csv: pd.DataFrame,
    reloaded_parquet: pd.DataFrame,
    required_columns: set[str],
) -> None:
    """재로딩한 파일의 데이터 개수와 컬럼을 검증한다."""
    assert len(reloaded_csv) == len(original), "CSV의 데이터 개수가 다릅니다."
    assert len(reloaded_parquet) == len(original), "Parquet의 데이터 개수가 다릅니다."
    
    assert set(reloaded_csv.columns) == set(original.columns), "CSV의 컬럼이 원본과 다릅니다."
    assert set(reloaded_parquet.columns) == set(original.columns), "Parquet의 컬럼이 원본과 다릅니다."

    assert required_columns.issubset(reloaded_csv.columns), "CSV에 필수 컬럼이 없습니다."
    assert required_columns.issubset(reloaded_parquet.columns), "Parquet에 필수 컬럼이 없습니다."